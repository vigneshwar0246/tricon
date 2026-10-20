import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * IntroPage — cinematic landing screen for the AI Voice Assistant.
 *
 * Layout (top → bottom):
 *   1. Header bar  – "AI VOICE ASSISTANT" overline + headline
 *   2. Video stage – the glass-sphere animation (never cropped/obstructed)
 *   3. Sub-copy    – tagline
 *   4. Footer bar  – "ENTER ASSISTANT →" button
 *
 * Text and the button are always in dedicated sections outside the video,
 * so the sphere and waveforms are never covered.
 */
export function IntroPage() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoFailed, setVideoFailed] = useState(false);
  const [exiting, setExiting] = useState(false);
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── autoplay ── */
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    try {
      const playPromise = el.play();
      if (playPromise !== undefined && typeof playPromise.catch === "function") {
        playPromise.catch(() => {
          /* autoplay blocked — video stays paused, UI still works */
        });
      }
    } catch {
      /* media playback invocation error in non-supporting runtime */
    }
  }, []);

  /* ── enter handler ── */
  const handleEnter = () => {
    if (exiting) return;
    sessionStorage.setItem("intro_seen", "1");
    if (prefersReducedMotion) {
      navigate("/", { replace: true });
      return;
    }
    setExiting(true);
    /* fade-out duration matches CSS transition (600 ms) */
    setTimeout(() => {
      navigate("/", { replace: true });
    }, 600);
  };

  /* ── keyboard: Enter / Space on the wrapper ── */
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleEnter();
    }
  };

  return (
    <div
      className={`intro-shell${exiting ? " intro-exit" : ""}`}
      onKeyDown={handleKey}
    >
      {/* ── 1. Header ── */}
      <header className="intro-header" aria-label="Intro header">
        <p className="intro-overline">AI VOICE ASSISTANT</p>
        <h1 className="intro-headline">Meet Your AI Voice Assistant.</h1>
      </header>

      {/* ── 2. Video stage ── */}
      <section className="intro-video-stage" aria-label="Intro animation">
        {!videoFailed ? (
          <video
            ref={videoRef}
            className="intro-video"
            src="/videos/intro-sphere.mp4"
            /* transparency: keep alpha channel if the codec supports it */
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-hidden="true"
            onError={() => setVideoFailed(true)}
          />
        ) : (
          /* Fallback: orange gradient placeholder so layout stays intact */
          <div className="intro-video-fallback" aria-hidden="true" />
        )}
      </section>

      {/* ── 3. Sub-copy ── */}
      <p className="intro-tagline">
        A more natural way to interact with AI.
      </p>

      {/* ── 4. Footer / CTA ── */}
      <footer className="intro-footer" aria-label="Intro actions">
        <button
          className="intro-enter-btn"
          onClick={handleEnter}
          aria-label="Enter the AI Voice Assistant"
          type="button"
        >
          ENTER ASSISTANT&nbsp;→
        </button>
      </footer>
    </div>
  );
}

