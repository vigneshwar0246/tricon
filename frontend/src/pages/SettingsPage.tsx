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
  return <div className="route-page"><header className="page-header"><p className="overline">Preferences</p><h1>Settings</h1><p>Model names and availability come from the backend. Language selection persists locally and applies to future text and voice turns.</p></header><Card className="settings-list">{settings.map(({ icon: Icon, title, value, note }) => <div className="setting-row" key={title}><span className="setting-icon"><Icon /></span><div><strong>{title}</strong><p>{note}</p></div><span className="setting-value">{value}</span></div>)}<div className="setting-row"><span className="setting-icon"><Languages /></span><div><strong>Conversation language</strong><p>Auto-detect each recording, or keep a manual choice until changed. Voice output requires a ready language voice.</p></div><select aria-label="Transcription language" className="setting-select" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">Automatic detection</option><option value="en">English{health.languageSupport?.en?.tts === false ? " (voice missing)" : ""}</option><option value="hi">Hindi{health.languageSupport?.hi?.tts === false ? " (voice missing)" : ""}</option><option value="ta">Tamil{health.languageSupport?.ta?.tts === false ? " (voice missing)" : ""}</option></select></div><div className="setting-row"><span className="setting-icon"><Server /></span><div><strong>CUDA diagnostics</strong><p>{diagnostics?.cuda.detail ?? "Diagnostics unavailable until the backend responds."}</p></div><span className="setting-value">{diagnostics?.cuda.inference_verified ? "Verified" : diagnostics ? "Not verified" : "Unknown"}</span></div><div className="setting-row"><span className="setting-icon"><Mic2 /></span><div><strong>STT device</strong><p>Last successful inference: {diagnostics?.stt.last_successful_device ?? "Not measured in this process"}</p></div><span className="setting-value">{diagnostics?.stt.configured_device ?? "Unknown"}</span></div></Card></div>;
}
