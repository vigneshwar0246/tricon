import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useHandsFree } from "./useHandsFree";

const options = () => ({
  silenceMs: 900,
  suspended: false,
  onCommand: vi.fn(async () => {}),
  onError: vi.fn(),
  onStatusChange: vi.fn(),
});

afterEach(() => vi.useRealTimers());

describe("hands-free shutdown", () => {
  it("releases a microphone permission result that arrives after Stop", async () => {
    const stopTrack = vi.fn();
    let resolvePermission!: (stream: MediaStream) => void;
    const permission = new Promise<MediaStream>((resolve) => { resolvePermission = resolve; });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(() => permission) },
    });
    vi.stubGlobal("MediaRecorder", class {});
    vi.stubGlobal("AudioContext", class { resume() { return Promise.resolve(); } close() { return Promise.resolve(); } });
    const callbacks = options();
    const { result } = renderHook(() => useHandsFree(callbacks));

    let pending!: Promise<void>;
    act(() => { pending = result.current.start(); });
    expect(result.current.status).toBe("permission");
    act(() => result.current.stop());
    await act(async () => {
      resolvePermission({ getTracks: () => [{ stop: stopTrack }] } as unknown as MediaStream);
      await pending;
    });

    expect(stopTrack).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("off");
    expect(callbacks.onStatusChange).not.toHaveBeenCalledWith("armed");
  });

  it("starts listening immediately and does not restart the recorder after Stop", async () => {
    vi.useFakeTimers();
    const stopTrack = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({
        getTracks: () => [{ stop: stopTrack }],
        getAudioTracks: () => [{ onended: null }],
      })) },
    });
    class MockAudioContext {
      currentTime = 0;
      destination = {};
      resume = vi.fn(async () => {});
      close = vi.fn(async () => {});
      createAnalyser() {
        return {
          fftSize: 1024,
          connect: vi.fn(),
          getFloatTimeDomainData: (samples: Float32Array) => {
            for (let index = 0; index < samples.length; index += 1) samples[index] = index % 4 === 0 ? 1 : -0.01;
          },
        };
      }
      createMediaStreamSource() { return { connect: vi.fn() }; }
      createOscillator() { return { frequency: { value: 0 }, connect: () => ({ connect: vi.fn() }), start: vi.fn(), stop: vi.fn() }; }
      createGain() { return { gain: { value: 0 }, connect: vi.fn() }; }
    }
    class MockRecorder {
      state: RecordingState = "inactive";
      onstop: (() => void) | null = null;
      ondataavailable: (() => void) | null = null;
      start() { this.state = "recording"; }
      stop() { this.state = "inactive"; window.setTimeout(() => this.onstop?.(), 0); }
    }
    vi.stubGlobal("AudioContext", MockAudioContext);
    vi.stubGlobal("MediaRecorder", MockRecorder);
    const callbacks = options();
    const { result } = renderHook(() => useHandsFree(callbacks));

    await act(async () => { await result.current.start(); });
    expect(result.current.status).toBe("capturing");
    act(() => result.current.stop());
    act(() => vi.advanceTimersByTime(0));

    expect(stopTrack).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("off");
    expect(callbacks.onStatusChange).toHaveBeenLastCalledWith("off");
  });

  it("restarts listening after a no-speech timeout without sending an empty turn", async () => {
    vi.useFakeTimers();
    const starts: number[] = [];
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({
        getTracks: () => [{ stop: vi.fn() }],
        getAudioTracks: () => [{ onended: null }],
      })) },
    });
    class MockAudioContext {
      currentTime = 0;
      destination = {};
      resume = vi.fn(async () => {});
      close = vi.fn(async () => {});
      createAnalyser() {
        return {
          fftSize: 512,
          connect: vi.fn(),
          getFloatTimeDomainData: (samples: Float32Array) => samples.fill(0),
        };
      }
      createMediaStreamSource() { return { connect: vi.fn() }; }
      createGain() { return { gain: { value: 0 }, connect: vi.fn() }; }
    }
    class MockRecorder {
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      onstop: (() => void) | null = null;
      ondataavailable: (() => void) | null = null;
      start() { this.state = "recording"; starts.push(Date.now()); }
      stop() { this.state = "inactive"; window.setTimeout(() => this.onstop?.(), 0); }
    }
    vi.stubGlobal("AudioContext", MockAudioContext);
    vi.stubGlobal("MediaRecorder", MockRecorder);
    const callbacks = options();
    const { result } = renderHook(() => useHandsFree(callbacks));

    await act(async () => { await result.current.start(); });
    expect(result.current.status).toBe("capturing");
    expect(starts).toHaveLength(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(5100); });

    expect(starts.length).toBeGreaterThanOrEqual(2);
    expect(callbacks.onCommand).not.toHaveBeenCalled();
    expect(result.current.status).toBe("capturing");
    act(() => result.current.stop());
  });

  it("requires sustained speech before barge-in and rearms capture without waiting for stale work", async () => {
    vi.useFakeTimers();
    let loud = true;
    const interruption = vi.fn();
    const command = vi.fn(() => new Promise<void>(() => {}));
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({
        getTracks: () => [{ stop: vi.fn() }],
        getAudioTracks: () => [{ onended: null }],
      })) },
    });
    class MockAudioContext {
      destination = {};
      resume = vi.fn(async () => {});
      close = vi.fn(async () => {});
      createAnalyser() {
        return { fftSize: 512, connect: vi.fn(),
          getFloatTimeDomainData: (samples: Float32Array) => samples.fill(loud ? 0.2 : 0.001) };
      }
      createMediaStreamSource() { return { connect: vi.fn() }; }
      createGain() { return { gain: { value: 0 }, connect: vi.fn() }; }
    }
    class MockRecorder {
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      onstop: (() => void) | null = null;
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      start() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["speech"], { type: this.mimeType }) });
        window.setTimeout(() => this.onstop?.(), 0);
      }
    }
    vi.stubGlobal("AudioContext", MockAudioContext);
    vi.stubGlobal("MediaRecorder", MockRecorder);
    const callbacks = { ...options(), onCommand: command, monitorInterruption: false, onInterruption: interruption };
    const { result, rerender } = renderHook(({ monitor }) => useHandsFree({ ...callbacks, monitorInterruption: monitor }),
      { initialProps: { monitor: false } });

    await act(async () => { await result.current.start(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(250); });
    loud = false;
    await act(async () => { await vi.advanceTimersByTimeAsync(950); });
    expect(command).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("processing");

    rerender({ monitor: true });
    loud = true;
    await act(async () => { await vi.advanceTimersByTimeAsync(40); });
    expect(interruption).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(20); });
    expect(interruption).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("capturing");
    act(() => result.current.stop());
  });

  it("respects warmup grace period and ignores noise below interruptionThreshold", async () => {
    vi.useFakeTimers();
    let sampleLevel = 0.04; // Moderate audio level (typical of speaker bleed)
    const interruption = vi.fn();
    const command = vi.fn(() => new Promise<void>(() => {}));
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({
        getTracks: () => [{ stop: vi.fn() }],
        getAudioTracks: () => [{ onended: null }],
      })) },
    });
    class MockAudioContext {
      destination = {};
      resume = vi.fn(async () => {});
      close = vi.fn(async () => {});
      createAnalyser() {
        return { fftSize: 512, connect: vi.fn(),
          getFloatTimeDomainData: (samples: Float32Array) => samples.fill(sampleLevel) };
      }
      createMediaStreamSource() { return { connect: vi.fn() }; }
      createGain() { return { gain: { value: 0 }, connect: vi.fn() }; }
    }
    class MockRecorder {
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      onstop: (() => void) | null = null;
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      start() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["speech"], { type: this.mimeType }) });
        window.setTimeout(() => this.onstop?.(), 0);
      }
    }
    vi.stubGlobal("AudioContext", MockAudioContext);
    vi.stubGlobal("MediaRecorder", MockRecorder);

    sampleLevel = 0.2; // User speaks to trigger capture
    const { result, rerender } = renderHook(
      ({ monitor }) => useHandsFree({
        ...options(),
        onCommand: command,
        monitorInterruption: monitor,
        onInterruption: interruption,
        interruptionWarmupMs: 500,
        interruptionThreshold: 0.065,
        interruptionDurationMs: 200,
      }),
      { initialProps: { monitor: false } },
    );

    await act(async () => { await result.current.start(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(250); });
    sampleLevel = 0.001; // Silence triggers command send
    await act(async () => { await vi.advanceTimersByTimeAsync(950); });
    expect(command).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("processing");

    // Assistant starts speaking; speaker bleed into mic is ~0.04
    rerender({ monitor: true });
    sampleLevel = 0.04;
    // Advance 600ms during assistant speech (bleed < interruptionThreshold)
    await act(async () => { await vi.advanceTimersByTimeAsync(600); });
    expect(interruption).not.toHaveBeenCalled();

    // Even if sampleLevel is loud (0.2), warmup for the first 500ms prevents interruption
    rerender({ monitor: false });
    rerender({ monitor: true });
    sampleLevel = 0.2;
    await act(async () => { await vi.advanceTimersByTimeAsync(300); }); // within warmup
    expect(interruption).not.toHaveBeenCalled();

    // After warmup (500ms total), sustained loud user speech (>200ms) triggers interruption
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(interruption).toHaveBeenCalledOnce();

    act(() => result.current.stop());
  });
});
