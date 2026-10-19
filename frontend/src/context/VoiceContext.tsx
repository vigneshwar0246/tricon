import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { deleteSession, getHealth, sendText, sendVoice } from "../lib/api";
import type { AssistantPhase, Message, Metrics, SystemHealth } from "../types";

interface VoiceContextValue {
  messages: Message[];
  phase: AssistantPhase;
  error: string | null;
  metrics: Metrics;
  language: string;
  health: SystemHealth;
  healthLoading: boolean;
  submitText: (text: string) => Promise<void>;
  toggleRecording: () => Promise<void>;
  clearConversation: () => void;
  refreshHealth: () => Promise<void>;
  setLanguage: (language: string) => void;
  setSpeaking: (speaking: boolean) => void;
}

const defaultHealth: SystemHealth = { api: "unknown", stt: "unknown", llm: "unknown", tts: "unknown" };
const VoiceContext = createContext<VoiceContextValue | null>(null);
const newId = () => crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<AssistantPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics>({});
  const [language, setLanguage] = useState("");
  const [health, setHealth] = useState<SystemHealth>(defaultHealth);
  const [healthLoading, setHealthLoading] = useState(false);
  const sessionId = useRef<string>(newId());
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);

  const addMessage = useCallback((role: Message["role"], content: string, audioUrl?: string) => {
    setMessages((current) => [...current, { id: newId(), role, content, audioUrl, createdAt: new Date().toISOString() }]);
  }, []);

  const handleError = useCallback((reason: unknown) => {
    const detail = reason instanceof Error ? reason.message : "Unknown error";
    setError(`Could not reach the local assistant. Confirm that the FastAPI backend is running, then try again. ${detail}`);
    setPhase("error");
  }, []);

  const submitText = useCallback(async (text: string) => {
    const clean = text.trim();
    if (!clean || phase === "processing") return;
    addMessage("user", clean);
    setError(null);
    setPhase("processing");
    try {
      const result = await sendText(clean, sessionId.current);
      sessionId.current = result.sessionId;
      addMessage("assistant", result.content, result.audioUrl);
      setMetrics(result.metrics);
      setPhase("idle");
    } catch (reason) { handleError(reason); }
  }, [addMessage, handleError, phase]);

  const stopRecording = useCallback(() => {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }, []);

  const toggleRecording = useCallback(async () => {
    if (phase === "listening") { stopRecording(); return; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      handleError(new Error("Microphone recording is not supported by this browser."));
      return;
    }
    try {
      setError(null);
      setPhase("requesting-permission");
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      chunks.current = [];
      recorder.current = new MediaRecorder(stream.current);
      recorder.current.addEventListener("dataavailable", (event) => { if (event.data.size) chunks.current.push(event.data); });
      recorder.current.addEventListener("stop", async () => {
        stream.current?.getTracks().forEach((track) => track.stop());
        setPhase("processing");
        try {
          const blob = new Blob(chunks.current, { type: recorder.current?.mimeType || "audio/webm" });
          const result = await sendVoice(blob, sessionId.current, language || undefined);
          sessionId.current = result.sessionId;
          addMessage("user", result.transcript);
          addMessage("assistant", result.content, result.audioUrl);
          setMetrics(result.metrics);
          setPhase("idle");
        } catch (reason) { handleError(reason); }
      }, { once: true });
      recorder.current.start();
      setPhase("listening");
    } catch (reason) {
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
      const denied = reason instanceof DOMException && reason.name === "NotAllowedError";
      handleError(new Error(denied ? "Microphone permission was denied." : reason instanceof Error ? reason.message : "Microphone access failed."));
    }
  }, [addMessage, handleError, language, phase, stopRecording]);

  const clearConversation = useCallback(async () => {
    const previousSession = sessionId.current;
    setMessages([]); setMetrics({}); setError(null); setPhase("idle"); sessionId.current = newId();
    try { await deleteSession(previousSession); }
    catch { setError("Conversation cleared on this device, but the backend could not confirm session deletion."); }
  }, []);

  const setSpeaking = useCallback((speaking: boolean) => {
    setPhase((current) => speaking ? "speaking" : current === "speaking" ? "idle" : current);
  }, []);

  const refreshHealth = useCallback(async () => {
    setHealthLoading(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4500);
    try { setHealth(await getHealth(controller.signal)); }
    catch { setHealth({ ...defaultHealth, api: "unavailable", checkedAt: new Date().toISOString() }); }
    finally { window.clearTimeout(timeout); setHealthLoading(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshHealth(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshHealth]);
  useEffect(() => () => stream.current?.getTracks().forEach((track) => track.stop()), []);

  const value = useMemo(() => ({ messages, phase, error, metrics, health, healthLoading, language, setLanguage, submitText, toggleRecording, clearConversation, refreshHealth, setSpeaking }), [messages, phase, error, metrics, health, healthLoading, language, submitText, toggleRecording, clearConversation, refreshHealth, setSpeaking]);
  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useVoice() {
  const context = useContext(VoiceContext);
  if (!context) throw new Error("useVoice must be used within VoiceProvider");
  return context;
}
