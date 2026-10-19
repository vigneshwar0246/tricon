import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeAudioFrame, ClapDetector, commandCaptureDecision } from "../lib/audioDetectors";

export type HandsFreeState = "off" | "permission" | "armed" | "wake-detected" | "capturing" | "processing" | "muted" | "error";

interface HandsFreeOptions {
  clapEnabled: boolean;
  clapThreshold: number;
  twoClaps: boolean;
  silenceMs: number;
  suspended: boolean;
  onCommand: (audio: Blob, commandEndedAt: number, captureMs: number) => Promise<void>;
  onError: (error: Error) => void;
  onStatusChange: (status: HandsFreeState) => void;
}

export function useHandsFree(options: HandsFreeOptions) {
  const [status, setStatus] = useState<HandsFreeState>("off");
  const [muted, setMuted] = useState(false);
  const statusRef = useRef<HandsFreeState>("off");
  const mutedRef = useRef(false);
  const optionsRef = useRef(options);
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const timerRef = useRef<number | null>(null);
  const activationTimerRef = useRef<number | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const startedAtRef = useRef(0);
  const lastSpeechRef = useRef<number | null>(null);
  const speechFramesRef = useRef(0);
  const noiseFloorRef = useRef(0.003);
  const discardRef = useRef(false);
  const generationRef = useRef(0);
  const detectorRef = useRef(new ClapDetector(options.clapThreshold, options.twoClaps));

  useEffect(() => { optionsRef.current = options; }, [options]);

  const changeStatus = useCallback((next: HandsFreeState) => {
    statusRef.current = next;
    setStatus(next);
    optionsRef.current.onStatusChange(next);
  }, []);

  const stop = useCallback(() => {
    generationRef.current += 1;
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    if (activationTimerRef.current !== null) window.clearTimeout(activationTimerRef.current);
    timerRef.current = null;
    activationTimerRef.current = null;
    discardRef.current = true;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void contextRef.current?.close();
    contextRef.current = null;
    analyserRef.current = null;
    changeStatus("off");
  }, [changeStatus]);

  const finishCapture = useCallback((discard: boolean) => {
    discardRef.current = discard;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  const startCapture = useCallback(() => {
    const stream = streamRef.current;
    if (!stream || statusRef.current !== "wake-detected") return;
    try {
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = () => {
        if (discardRef.current || !chunks.length) {
          changeStatus(mutedRef.current ? "muted" : "armed");
          return;
        }
        const generation = generationRef.current;
        changeStatus("processing");
        const audio = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        void optionsRef.current.onCommand(audio, lastSpeechRef.current ?? performance.now(), performance.now() - startedAtRef.current).catch((error: unknown) => {
          optionsRef.current.onError(error instanceof Error ? error : new Error("Voice request failed."));
        }).finally(() => {
          if (generation === generationRef.current) changeStatus(mutedRef.current ? "muted" : "armed");
        });
      };
      recorder.start();
      startedAtRef.current = performance.now();
      lastSpeechRef.current = null;
      speechFramesRef.current = 0;
      discardRef.current = false;
      changeStatus("capturing");
    } catch (error) {
      optionsRef.current.onError(error instanceof Error ? error : new Error("Microphone recording failed."));
      changeStatus("armed");
    }
  }, [changeStatus]);

  const tick = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser || optionsRef.current.suspended) return;
    const samples = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(samples);
    const frame = analyzeAudioFrame(samples);
    const now = performance.now();
    if (statusRef.current === "armed") {
      noiseFloorRef.current = Math.min(0.03, noiseFloorRef.current * 0.97 + frame.rms * 0.03);
      if (!optionsRef.current.clapEnabled || !detectorRef.current.accept(frame, now)) return;
      changeStatus("wake-detected");
      const context = contextRef.current;
      if (context) {
        const tone = context.createOscillator();
        const gain = context.createGain();
        gain.gain.value = 0.035;
        tone.frequency.value = 880;
        tone.connect(gain).connect(context.destination);
        tone.start();
        tone.stop(context.currentTime + 0.09);
      }
      activationTimerRef.current = window.setTimeout(startCapture, 180);
    } else if (statusRef.current === "capturing") {
      const speech = frame.rms > Math.max(0.015, noiseFloorRef.current * 2.7);
      speechFramesRef.current = speech ? speechFramesRef.current + 1 : 0;
      if (speechFramesRef.current >= 2) lastSpeechRef.current = now;
      const decision = commandCaptureDecision(now, startedAtRef.current, lastSpeechRef.current, optionsRef.current.silenceMs);
      if (decision !== "continue") finishCapture(decision === "discard");
    }
  }, [changeStatus, finishCapture, startCapture]);

  const start = useCallback(async () => {
    if (statusRef.current !== "off" && statusRef.current !== "error") return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !window.AudioContext) {
      optionsRef.current.onError(new Error("This browser does not support local microphone capture."));
      changeStatus("error");
      return;
    }
    const generation = generationRef.current;
    changeStatus("permission");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      if (generation !== generationRef.current) { stream.getTracks().forEach((track) => track.stop()); return; }
      const context = new AudioContext();
      await context.resume();
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);
      stream.getAudioTracks().forEach((track) => { track.onended = () => { optionsRef.current.onError(new Error("Microphone disconnected.")); stop(); }; });
      streamRef.current = stream;
      contextRef.current = context;
      analyserRef.current = analyser;
      noiseFloorRef.current = 0.003;
      detectorRef.current = new ClapDetector(optionsRef.current.clapThreshold, optionsRef.current.twoClaps);
      changeStatus(mutedRef.current ? "muted" : "armed");
      timerRef.current = window.setInterval(tick, 50);
    } catch (error) {
      stop();
      optionsRef.current.onError(error instanceof Error ? error : new Error("Microphone permission failed."));
      changeStatus("error");
    }
  }, [changeStatus, stop, tick]);

  const toggleMute = useCallback(() => {
    const next = !mutedRef.current;
    mutedRef.current = next;
    setMuted(next);
    if (next && statusRef.current === "capturing") finishCapture(true);
    if (statusRef.current === "armed" || statusRef.current === "muted") changeStatus(next ? "muted" : "armed");
  }, [changeStatus, finishCapture]);

  useEffect(() => {
    detectorRef.current = new ClapDetector(options.clapThreshold, options.twoClaps);
  }, [options.clapThreshold, options.twoClaps]);
  useEffect(() => () => stop(), [stop]);

  return { status, muted, start, stop, toggleMute };
}
