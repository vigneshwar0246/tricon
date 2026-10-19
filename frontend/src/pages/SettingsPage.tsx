import { Headphones, Languages, Mic2, Server } from "lucide-react";
import { Card } from "../components/ui/card";

const settings = [
  { icon: Mic2, title: "Speech recognition", value: "Faster-Whisper", note: "Configured by the local backend" },
  { icon: Server, title: "Language model", value: "Qwen 2.5 3B", note: "Served through Ollama" },
  { icon: Headphones, title: "Speech synthesis", value: "Piper or Kokoro", note: "Selected by the local backend" },
  { icon: Languages, title: "Language", value: "Automatic", note: "Detected from each recording" },
];

export function SettingsPage() {
  return <div className="route-page"><header className="page-header"><p className="overline">Preferences</p><h1>Settings</h1><p>Model configuration is read from the backend. This frontend does not report unverified model state.</p></header><Card className="settings-list">{settings.map(({ icon: Icon, title, value, note }) => <div className="setting-row" key={title}><span className="setting-icon"><Icon /></span><div><strong>{title}</strong><p>{note}</p></div><span className="setting-value">{value}</span></div>)}</Card></div>;
}
