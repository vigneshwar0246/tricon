import { AudioLines, Cpu, LockKeyhole } from "lucide-react";
import { Card } from "../components/ui/card";

export function AboutPage() {
  return (
    <div className="route-page about-page">
      <header className="page-header"><p className="overline">About the project</p><h1>Open models. Local voice.</h1><p>AI Voice Assistant is an internship project built to explore a complete speech-to-speech pipeline with open-weight models.</p></header>
      <div className="about-grid">
        <Card><AudioLines /><h2>Natural interaction</h2><p>Speak normally, receive a transcription, and continue the same conversation over multiple turns.</p></Card>
        <Card><Cpu /><h2>Open-weight stack</h2><p>Faster-Whisper, Qwen through Ollama, and local speech synthesis can run behind the interface.</p></Card>
        <Card><LockKeyhole /><h2>Honest system state</h2><p>The dashboard displays status and latency only when the backend returns real health and timing data.</p></Card>
      </div>
    </div>
  );
}
