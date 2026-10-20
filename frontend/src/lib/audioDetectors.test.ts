import { describe, expect, it } from "vitest";
import { commandCaptureDecision } from "./audioDetectors";

describe("voice activity endpointing", () => {
  it("stops after silence or maximum duration and discards no-speech timeouts", () => {
    expect(commandCaptureDecision(4900, 0, null, 800)).toBe("continue");
    expect(commandCaptureDecision(5000, 0, null, 800)).toBe("discard");
    expect(commandCaptureDecision(1800, 0, 900, 800)).toBe("send");
    expect(commandCaptureDecision(12000, 0, 11000, 800)).toBe("send");
  });
});
