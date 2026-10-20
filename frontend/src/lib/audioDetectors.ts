export interface AudioFrame {
  rms: number;
  peak: number;
  zeroCrossingRate: number;
}

export function analyzeAudioFrame(samples: Float32Array): AudioFrame {
  let energy = 0;
  let peak = 0;
  let crossings = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index];
    energy += value * value;
    peak = Math.max(peak, Math.abs(value));
    if (index && (value >= 0) !== (samples[index - 1] >= 0)) crossings += 1;
  }
  return {
    rms: Math.sqrt(energy / Math.max(samples.length, 1)),
    peak,
    zeroCrossingRate: crossings / Math.max(samples.length - 1, 1),
  };
}

export function commandCaptureDecision(
  now: number,
  startedAt: number,
  lastSpeechAt: number | null,
  silenceMs: number,
  maxDurationMs = 12000,
  speechTimeoutMs = 5000,
): "continue" | "send" | "discard" {
  if (now - startedAt >= maxDurationMs) return lastSpeechAt === null ? "discard" : "send";
  if (lastSpeechAt === null) return now - startedAt >= speechTimeoutMs ? "discard" : "continue";
  return now - lastSpeechAt >= silenceMs ? "send" : "continue";
}
