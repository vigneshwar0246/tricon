import type { Metrics, ServiceState, SystemHealth } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

type UnknownRecord = Record<string, unknown>;

function readPath(source: UnknownRecord, paths: string[]): unknown {
  for (const path of paths) {
    const result = path.split(".").reduce<unknown>((value, key) => {
      return value && typeof value === "object" ? (value as UnknownRecord)[key] : undefined;
    }, source);
    if (result !== undefined && result !== null) return result;
  }
}

function readNumber(source: UnknownRecord, paths: string[]) {
  const value = readPath(source, paths);
  return typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : undefined;
}

function parseMetrics(data: UnknownRecord, measuredTotal: number): Metrics {
  return {
    sttMs: readNumber(data, ["metrics.stt_ms", "timings.stt_ms", "stt_ms"]),
    llmMs: readNumber(data, ["metrics.llm_ms", "timings.llm_ms", "llm_ms"]),
    ttsMs: readNumber(data, ["metrics.tts_ms", "timings.tts_ms", "tts_ms"]),
    totalMs: readNumber(data, ["metrics.total_ms", "timings.total_ms", "total_ms"]) ?? measuredTotal,
  };
}

async function parseResponse(response: Response) {
  if (!response.ok) throw new Error(`The local API returned ${response.status}.`);
  return response.json() as Promise<UnknownRecord>;
}

export async function sendText(message: string, sessionId: string) {
  const started = performance.now();
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = await parseResponse(response);
  const content = readPath(data, ["response", "message", "text", "assistant_text"]);
  if (typeof content !== "string" || !content.trim()) throw new Error("The API response did not contain assistant text.");
  const audio = readPath(data, ["audio_url", "audio.url", "tts_url"]);
  return { content, audioUrl: typeof audio === "string" ? audio : undefined, metrics: parseMetrics(data, performance.now() - started) };
}

export async function sendVoice(blob: Blob, sessionId: string) {
  const body = new FormData();
  body.append("audio", blob, blob.type.includes("ogg") ? "voice.ogg" : "voice.webm");
  body.append("session_id", sessionId);
  const started = performance.now();
  const data = await parseResponse(await fetch(`${API_BASE}/api/voice`, { method: "POST", body }));
  const transcript = readPath(data, ["transcript", "user_text", "input"]);
  const content = readPath(data, ["response", "message", "text", "assistant_text"]);
  const audio = readPath(data, ["audio_url", "audio.url", "tts_url"]);
  if (typeof content !== "string" || !content.trim()) throw new Error("The API response did not contain assistant text.");
  return {
    transcript: typeof transcript === "string" ? transcript : "Voice message",
    content,
    audioUrl: typeof audio === "string" ? audio : undefined,
    metrics: parseMetrics(data, performance.now() - started),
  };
}

function toServiceState(value: unknown): ServiceState {
  if (value === true || ["ready", "online", "healthy", "ok"].includes(String(value).toLowerCase())) return "ready";
  if (value === undefined || value === null) return "unknown";
  return "unavailable";
}

export async function getHealth(signal?: AbortSignal): Promise<SystemHealth> {
  const data = await parseResponse(await fetch(`${API_BASE}/api/health`, { signal }));
  const services = (data.services ?? data.components ?? {}) as UnknownRecord;
  return {
    api: toServiceState(data.status ?? true),
    stt: toServiceState(services.stt),
    llm: toServiceState(services.llm),
    tts: toServiceState(services.tts),
    checkedAt: new Date().toISOString(),
  };
}
