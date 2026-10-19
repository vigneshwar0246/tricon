import { Bot, Cpu, RefreshCw, Server, Speech } from "lucide-react";
import { useVoice } from "../context/VoiceContext";
import type { ServiceState } from "../types";
import { Card } from "./ui/card";

const label: Record<ServiceState, string> = { unknown: "Not checked", ready: "Ready", unavailable: "Unavailable" };

export function StatusPanel() {
  const { health, healthLoading, refreshHealth } = useVoice();
  const services = [
    { name: "Speech-to-Text", model: health.models?.stt ?? "Faster-Whisper", state: health.stt, icon: Speech },
    { name: "Language Model", model: health.models?.llm ?? "Ollama", state: health.llm, icon: Bot },
    { name: "Text-to-Speech", model: health.models?.tts?.replaceAll("_", " ") ?? "Piper", state: health.tts, icon: Cpu },
    { name: "Backend API", model: "Local FastAPI service", state: health.api, icon: Server },
  ];
  return (
    <Card className="status-card">
      <div className="card-header"><div><p className="overline">Connection</p><h2>System status</h2></div><button className="refresh-button" onClick={() => void refreshHealth()} disabled={healthLoading} aria-label="Refresh system status"><RefreshCw className={healthLoading ? "spinning" : ""} /></button></div>
      <div className="service-list">
        {services.map(({ name, model, state, icon: Icon }) => (
          <div className="service-row" key={name}>
            <span className="service-icon"><Icon aria-hidden="true" /></span>
            <div className="service-copy"><strong>{name}</strong><span>{model}</span></div>
            <span className={`status-tag ${state}`}><i aria-hidden="true" />{label[state]}</span>
          </div>
        ))}
      </div>
      <p className="status-note">Status appears only after a response from the local backend.</p>
    </Card>
  );
}
