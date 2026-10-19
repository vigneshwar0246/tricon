import type { Metrics, ServiceState, SystemHealth } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

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
  const data = await response.json().catch(() => ({})) as UnknownRecord;
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : `The local API returned ${response.status}.`);
  }
  return data;
}

function resolveAudioUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  try { return new URL(value, API_BASE || window.location.origin).toString(); }
  catch { return undefined; }
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
  return { content, audioUrl: resolveAudioUrl(audio), sessionId: String(data.session_id ?? sessionId), metrics: parseMetrics(data, performance.now() - started) };
}

export async function sendVoice(blob: Blob, sessionId: string, language?: string) {
  const body = new FormData();
  const extension = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "mp4" : "webm";
  body.append("audio", blob, `voice.${extension}`);
  body.append("session_id", sessionId);
  if (language) body.append("language", language);
  const started = performance.now();
  const data = await parseResponse(await fetch(`${API_BASE}/api/voice`, { method: "POST", body }));
  const transcript = readPath(data, ["transcript", "user_text", "input"]);
  const content = readPath(data, ["response", "message", "text", "assistant_text"]);
  const audio = readPath(data, ["audio_url", "audio.url", "tts_url"]);
  const audioUrl = resolveAudioUrl(audio);
  if (typeof transcript !== "string" || !transcript.trim()) throw new Error("The API response did not contain a transcription.");
  if (typeof content !== "string" || !content.trim()) throw new Error("The API response did not contain assistant text.");
  if (!audioUrl) throw new Error("The API response did not contain playable assistant audio.");
  return {
    transcript,
    content,
    audioUrl,
    sessionId: String(data.session_id ?? sessionId),
    metrics: parseMetrics(data, performance.now() - started),
  };
}

export async function deleteSession(sessionId: string): Promise<void> {
  await parseResponse(await fetch(`${API_BASE}/api/chat/${encodeURIComponent(sessionId)}`, { method: "DELETE" }));
}

function toServiceState(value: unknown): ServiceState {
  if (value === true || ["ready", "online", "healthy", "ok"].includes(String(value).toLowerCase())) return "ready";
  if (value === undefined || value === null) return "unknown";
  return "unavailable";
}

export async function getHealth(signal?: AbortSignal): Promise<SystemHealth> {
  const data = await parseResponse(await fetch(`${API_BASE}/api/health`, { signal }));
  const services = (data.services ?? data.components ?? {}) as UnknownRecord;
  const backend = (data.backend ?? {}) as UnknownRecord;
  const models = (data.models ?? {}) as UnknownRecord;
  return {
    api: toServiceState(services.api ?? backend.available),
    stt: toServiceState(services.stt),
    llm: toServiceState(services.llm),
    tts: toServiceState(services.tts),
    models: {
      stt: typeof models.stt === "string" ? models.stt : undefined,
      llm: typeof models.llm === "string" ? models.llm : undefined,
      tts: typeof models.tts === "string" ? models.tts : undefined,
      language: typeof models.language === "string" ? models.language : undefined,
    },
    checkedAt: new Date().toISOString(),
  };
}
