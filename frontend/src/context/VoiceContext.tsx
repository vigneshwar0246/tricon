import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { deleteSession, getHealth, sendText, sendVoice, streamVoice } from "../lib/api";
import { useHandsFree } from "../hooks/useHandsFree";
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
  handsFreeStatus: string;
  handsFreeMuted: boolean;
  silenceMs: number;
  setSilenceMs: (duration: number) => void;
  startHandsFree: () => Promise<void>;
  stopHandsFree: () => void;
  toggleHandsFreeMute: () => void;
  stopSpeaking: () => void;
  bargeInEnabled: boolean;
  setBargeInEnabled: (enabled: boolean) => void;
}

const defaultHealth: SystemHealth = { api: "unknown", stt: "unknown", llm: "unknown", tts: "unknown" };
const VoiceContext = createContext<VoiceContextValue | null>(null);
const newId = () => crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<AssistantPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics>({});
  const [language, setLanguageState] = useState(() => localStorage.getItem("trikon-language") ?? "");
  const [health, setHealth] = useState<SystemHealth>(defaultHealth);
  const [healthLoading, setHealthLoading] = useState(false);
  const sessionId = useRef<string>(newId());
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const [silenceMs, setSilenceMs] = useState(900);
  const [bargeInEnabled, setBargeInEnabled] = useState(true);
  const playback = useRef<HTMLAudioElement | null>(null);
  const finishPlayback = useRef<(() => void) | null>(null);
  const stopHandsFreeRef = useRef<(() => void) | null>(null);
  const handsFreeAbort = useRef<AbortController | null>(null);
  const turnGeneration = useRef(0);

  const addMessage = useCallback((role: Message["role"], content: string, audioUrl?: string) => {
    setMessages((current) => [...current, { id: newId(), role, content, audioUrl, createdAt: new Date().toISOString() }]);
  }, []);

  const handleError = useCallback((reason: unknown) => {
    const detail = reason instanceof Error ? reason.message : "Unknown error";
    setError(`Could not reach the local assistant. Confirm that the FastAPI backend is running, then try again. ${detail}`);
    setPhase("error");
  }, []);

  const stopSpeaking = useCallback(() => {
    window.dispatchEvent(new Event("ai-voice-stop-speech"));
    if (playback.current) { playback.current.pause(); playback.current.currentTime = 0; }
    playback.current = null;
    finishPlayback.current?.();
    finishPlayback.current = null;
  }, []);

  const setLanguage = useCallback((next: string) => {
    turnGeneration.current += 1;
    handsFreeAbort.current?.abort();
    stopSpeaking();
    setLanguageState(next);
    localStorage.setItem("trikon-language", next);
  }, [stopSpeaking]);

  const handleHandsFreeCommand = useCallback(async (blob: Blob, commandEndedAt: number, captureMs: number, vadEndMs: number) => {
    const generation = ++turnGeneration.current;
    setPhase("processing");
    const controller = new AbortController();
    handsFreeAbort.current = controller;
    let playbackChain = Promise.resolve();
    let assistantText = "";
    let resultMetrics: Metrics = {};
    let action: string | undefined;
    const playChunk = (url: string) => new Promise<void>((resolve, reject) => {
      if (generation !== turnGeneration.current) { resolve(); return; }
      const audio = new Audio(url);
      playback.current = audio;
      finishPlayback.current = resolve;
      audio.onplaying = () => {
        setPhase("speaking");
        setMetrics((current) => ({ ...current, firstAudioMs: current.firstAudioMs ?? Math.round(performance.now() - commandEndedAt) }));
      };
      audio.onended = () => resolve();
      audio.onerror = () => reject(new Error("Generated speech could not be played."));
      void audio.play().catch(reject);
    });
    try {
      await streamVoice(blob, sessionId.current, language || undefined, controller.signal, (event) => {
        if (generation !== turnGeneration.current) return;
        if (event.type === "transcript" && event.transcript) {
          setPhase("generating");
          addMessage("user", event.transcript);
          if (!language && event.language) setLanguageState(event.language);
        } else if (event.type === "text") {
          assistantText += event.delta ?? "";
        } else if (event.type === "audio" && event.url) {
          playbackChain = playbackChain.then(() => playChunk(event.url!));
        } else if (event.type === "done") {
          sessionId.current = event.session_id ?? sessionId.current;
          action = event.action;
          const raw = event.metrics ?? {};
          resultMetrics = {
            sttMs: Number(raw.stt_ms) || undefined, llmMs: Number(raw.llm_ms) || undefined,
            ttsMs: Number(raw.tts_ms) || undefined, totalMs: Number(raw.total_ms) || undefined,
            firstTokenMs: Number(raw.first_token_ms) || undefined,
          };
          if (action === "clear_conversation") setMessages([]);
          addMessage("assistant", event.response || assistantText);
          setMetrics({ ...resultMetrics, captureMs, vadEndMs });
        }
      });
      await playbackChain;
    } finally {
      if (handsFreeAbort.current === controller) handsFreeAbort.current = null;
      playback.current = null;
      finishPlayback.current = null;
    }
    if (controller.signal.aborted || generation !== turnGeneration.current) throw new DOMException("Voice request cancelled.", "AbortError");
    if (action === "stop_listening") stopHandsFreeRef.current?.();
    setPhase("idle");
  }, [addMessage, language]);

  const handsFree = useHandsFree({
    silenceMs,
    suspended: phase === "processing" || phase === "generating",
    monitorInterruption: bargeInEnabled && phase === "speaking",
    onInterruption: () => {
      turnGeneration.current += 1;
      handsFreeAbort.current?.abort();
      stopSpeaking();
      setPhase("interrupted");
    },
    onCommand: handleHandsFreeCommand,
    onError: handleError,
    onStatusChange: (status) => {
      if (status === "armed") setPhase("armed");
      if (status === "capturing") setPhase("listening");
      if (status === "muted" || status === "off") setPhase("idle");
    },
  });
  const stopHandsFreeHook = handsFree.stop;
  const stopHandsFree = useCallback(() => {
    handsFreeAbort.current?.abort();
    stopSpeaking();
    stopHandsFreeHook();
  }, [stopHandsFreeHook, stopSpeaking]);
  useEffect(() => { stopHandsFreeRef.current = stopHandsFree; }, [stopHandsFree]);

  const submitText = useCallback(async (text: string) => {
    const clean = text.trim();
    if (!clean || phase === "processing") return;
    addMessage("user", clean);
    setError(null);
    setPhase("processing");
    try {
      const result = await sendText(clean, sessionId.current, language || undefined);
      sessionId.current = result.sessionId;
      addMessage("assistant", result.content, result.audioUrl);
      setMetrics(result.metrics);
      setPhase("idle");
    } catch (reason) { handleError(reason); }
  }, [addMessage, handleError, language, phase]);

  const stopRecording = useCallback(() => {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }, []);

  const toggleRecording = useCallback(async () => {
    if (handsFree.status !== "off" && handsFree.status !== "error") {
      handleError(new Error("Turn off hands-free mode before using tap-to-record."));
      return;
    }
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
          if (result.action === "clear_conversation") setMessages([]);
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
  }, [addMessage, handleError, handsFree.status, language, phase, stopRecording]);

  const clearConversation = useCallback(async () => {
    const previousSession = sessionId.current;
    setMessages([]); setMetrics({}); setError(null); setPhase("idle"); sessionId.current = newId();
    try { await deleteSession(previousSession); }
    catch { setError("Conversation cleared on this device, but the backend could not confirm session deletion."); }
  }, []);

  const setSpeaking = useCallback((speaking: boolean) => {
    setPhase((current) => speaking ? "speaking" : current === "speaking" ? handsFree.status === "armed" ? "armed" : "idle" : current);
  }, [handsFree.status]);

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

  const value = useMemo(() => ({
    messages, phase, error, metrics, health, healthLoading, language, setLanguage, submitText,
    toggleRecording, clearConversation, refreshHealth, setSpeaking,
    handsFreeStatus: handsFree.status, handsFreeMuted: handsFree.muted,
    silenceMs, setSilenceMs,
    startHandsFree: handsFree.start, stopHandsFree,
    toggleHandsFreeMute: handsFree.toggleMute, stopSpeaking,
    bargeInEnabled, setBargeInEnabled,
  }), [messages, phase, error, metrics, health, healthLoading, language, setLanguage, submitText, toggleRecording, clearConversation, refreshHealth, setSpeaking, handsFree.status, handsFree.muted, handsFree.start, handsFree.toggleMute, stopHandsFree, silenceMs, stopSpeaking, bargeInEnabled]);
  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useVoice() {
  const context = useContext(VoiceContext);
  if (!context) throw new Error("useVoice must be used within VoiceProvider");
  return context;
}
