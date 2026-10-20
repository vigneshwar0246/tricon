export type AssistantPhase = "idle" | "requesting-permission" | "armed" | "listening" | "processing" | "speaking" | "error";
export type ServiceState = "unknown" | "ready" | "unavailable";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  audioUrl?: string;
}

export interface Metrics {
  sttMs?: number;
  llmMs?: number;
  ttsMs?: number;
  totalMs?: number;
  firstAudioMs?: number;
  captureMs?: number;
  vadEndMs?: number;
}

export interface SystemHealth {
  api: ServiceState;
  stt: ServiceState;
  llm: ServiceState;
  tts: ServiceState;
  models?: { stt?: string; llm?: string; tts?: string; language?: string };
  checkedAt?: string;
}
