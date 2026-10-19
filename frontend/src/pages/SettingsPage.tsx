import { Headphones, Languages, Mic2, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { Card } from "../components/ui/card";
import { useVoice } from "../context/VoiceContext";
import { getDiagnostics, type RuntimeDiagnostics } from "../lib/api";

export function SettingsPage() {
  const { health, language, setLanguage } = useVoice();
  const [diagnostics, setDiagnostics] = useState<RuntimeDiagnostics | null>(null);
  useEffect(() => { void getDiagnostics().then(setDiagnostics).catch(() => setDiagnostics(null)); }, []);
  const settings = [
    { icon: Mic2, title: "Speech recognition", value: health.models?.stt ?? "Not reported", note: health.stt === "ready" ? "Local model files are available" : "Configured by the local backend" },
    { icon: Server, title: "Language model", value: health.models?.llm ?? "Not reported", note: health.llm === "ready" ? "Available through Ollama" : "Model readiness requires the backend check" },
    { icon: Headphones, title: "Speech synthesis", value: health.models?.tts?.replaceAll("_", " ") ?? "Not reported", note: health.tts === "ready" ? "Local voice files are available" : "Selected by the local backend" },
  ];
  return <div className="route-page"><header className="page-header"><p className="overline">Preferences</p><h1>Settings</h1><p>Model names and availability come from the backend. Language overrides affect future voice recordings.</p></header><Card className="settings-list">{settings.map(({ icon: Icon, title, value, note }) => <div className="setting-row" key={title}><span className="setting-icon"><Icon /></span><div><strong>{title}</strong><p>{note}</p></div><span className="setting-value">{value}</span></div>)}<div className="setting-row"><span className="setting-icon"><Languages /></span><div><strong>Transcription language</strong><p>Applies to browser-recorded voice messages</p></div><select aria-label="Transcription language" className="setting-select" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">Backend default ({health.models?.language ?? "not reported"})</option><option value="en">English</option><option value="hi">Hindi</option><option value="ta">Tamil</option></select></div><div className="setting-row"><span className="setting-icon"><Server /></span><div><strong>CUDA diagnostics</strong><p>{diagnostics?.cuda.detail ?? "Diagnostics unavailable until the backend responds."}</p></div><span className="setting-value">{diagnostics?.cuda.inference_verified ? "Verified" : diagnostics ? "Not verified" : "Unknown"}</span></div><div className="setting-row"><span className="setting-icon"><Mic2 /></span><div><strong>STT device</strong><p>Last successful inference: {diagnostics?.stt.last_successful_device ?? "Not measured in this process"}</p></div><span className="setting-value">{diagnostics?.stt.configured_device ?? "Unknown"}</span></div></Card></div>;
}
