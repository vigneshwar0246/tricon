import { describe, expect, it } from "vitest";
import { analyzeAudioFrame, ClapDetector, commandCaptureDecision } from "./audioDetectors";

describe("local audio detection", () => {
  it("rejects speech-like tones and steady noise but accepts a sharp broadband clap", () => {
    const detector = new ClapDetector(0.08, false);
    const tone = Float32Array.from({ length: 1024 }, (_, index) => Math.sin(index * Math.PI / 40) * 0.2);
    const quiet = new Float32Array(1024);
    const clap = Float32Array.from({ length: 1024 }, (_, index) => ((index * 73 % 101) / 50.5 - 1) * (index < 180 ? 0.7 : 0.02));
    expect(detector.accept(analyzeAudioFrame(tone), 100)).toBe(false);
    detector.accept(analyzeAudioFrame(quiet), 150);
    expect(detector.accept(analyzeAudioFrame(clap), 200)).toBe(true);
    expect(detector.accept(analyzeAudioFrame(clap), 250)).toBe(false);
  });

  it("requires two separated transients when enabled", () => {
    const detector = new ClapDetector(0.08, true);
    const clap = { rms: 0.2, peak: 0.7, zeroCrossingRate: 0.4 };
    const quiet = { rms: 0.001, peak: 0.002, zeroCrossingRate: 0.1 };
    expect(detector.accept(clap, 1000)).toBe(false);
    detector.accept(quiet, 1100);
    expect(detector.accept(clap, 1500)).toBe(true);
  });

  it("stops after silence or maximum duration and discards no-speech timeouts", () => {
    expect(commandCaptureDecision(4900, 0, null, 800)).toBe("continue");
    expect(commandCaptureDecision(5000, 0, null, 800)).toBe("discard");
    expect(commandCaptureDecision(1800, 0, 900, 800)).toBe("send");
    expect(commandCaptureDecision(12000, 0, 11000, 800)).toBe("send");
  });
});
