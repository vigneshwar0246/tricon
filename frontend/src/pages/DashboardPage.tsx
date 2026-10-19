import { motion, useReducedMotion } from "framer-motion";
import { Conversation } from "../components/Conversation";
import { PerformancePanel } from "../components/PerformancePanel";
import { StatusPanel } from "../components/StatusPanel";
import { VoiceOrb } from "../components/VoiceOrb";
import { useVoice } from "../context/VoiceContext";

const prompts = ["What can you do?", "Explain AI simply", "Tell me about Tamil Nadu", "Switch to Hindi"];

export function DashboardPage() {
  const { submitText } = useVoice();
  const reduced = useReducedMotion();
  return (
    <div className="dashboard-grid">
      <div className="dashboard-main">
        <motion.section className="hero" initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .45 }}>
          <div className="hero-copy"><p className="overline">Local voice intelligence</p><h1>Hello!</h1><p className="hero-subtitle">Your voice, my intelligence.</p><p className="hero-description">Talk naturally. I’ll listen, understand and respond, all locally.</p></div>
          <VoiceOrb />
          <div className="prompt-list" aria-label="Example prompts">{prompts.map((prompt) => <button key={prompt} onClick={() => void submitText(prompt)}>{prompt}</button>)}</div>
        </motion.section>
        <Conversation />
      </div>
      <aside className="dashboard-side" aria-label="System information"><StatusPanel /><PerformancePanel /></aside>
    </div>
  );
}
