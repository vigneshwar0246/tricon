import { Mic, Square } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { useEffect } from "react";
import { useVoice } from "../context/VoiceContext";

const phaseCopy = {
  idle: ["Tap to speak", "or press the spacebar"],
  "requesting-permission": ["Opening microphone", "check your browser permission"],
  armed: ["Hands-free ready", "starting microphone"],
  listening: ["Listening", "pause when you are done speaking"],
  transcribing: ["Transcribing", "recognizing your speech locally"],
  generating: ["Generating", "the local model is answering"],
  processing: ["Thinking", "your local models are working"],
  speaking: ["Speaking", "playing the generated response"],
  interrupted: ["Interrupted", "listening to your new request"],
  error: ["Ready to try again", "check the message below"],
} as const;

export function VoiceOrb() {
  const { phase, toggleRecording } = useVoice();
  const reduced = useReducedMotion();
  const listening = phase === "listening";
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Space" && !["INPUT", "TEXTAREA", "BUTTON"].includes((document.activeElement?.tagName ?? ""))) {
        event.preventDefault(); void toggleRecording();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggleRecording]);

  return (
    <div className="voice-control">
      <div className={`wave-bars ${listening ? "active" : ""}`} aria-hidden="true">{[8,18,28,14,22,10].map((height, index) => <i key={index} style={{ height }} />)}</div>
      <motion.button
        className={`voice-button ${listening ? "listening" : ""}`}
        onClick={() => void toggleRecording()}
        whileTap={reduced ? undefined : { scale: 0.96 }}
        animate={listening && !reduced ? { scale: [1, 1.04, 1] } : { scale: 1 }}
        transition={listening ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" } : undefined}
        aria-label={listening ? "Stop listening" : "Start listening"}
      >
        <span className="voice-button-inner">{listening ? <Square fill="currentColor" /> : <Mic />}</span>
      </motion.button>
      <div className={`wave-bars mirrored ${listening ? "active" : ""}`} aria-hidden="true">{[8,18,28,14,22,10].map((height, index) => <i key={index} style={{ height }} />)}</div>
      <div className="voice-copy" aria-live="polite"><strong>{phaseCopy[phase][0]}</strong><span>{phaseCopy[phase][1]}</span></div>
    </div>
  );
}
