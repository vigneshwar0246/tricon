import { Activity } from "lucide-react";
import { useVoice } from "../context/VoiceContext";
import { formatDuration } from "../lib/utils";
import { Card } from "./ui/card";

export function PerformancePanel() {
  const { metrics } = useVoice();
  const rows = [["STT processing", metrics.sttMs], ["LLM response", metrics.llmMs], ["TTS generation", metrics.ttsMs]] as const;
  return (
    <Card className="performance-card">
      <div className="card-header"><div><p className="overline">Last response</p><h2>Performance</h2></div><span className="header-icon"><Activity /></span></div>
      <div className="metric-list">
        {rows.map(([name, value]) => <div className="metric-row" key={name}><span>{name}</span><strong>{formatDuration(value)}</strong></div>)}
        <div className="metric-row metric-total"><span>Total latency</span><strong>{formatDuration(metrics.totalMs)}</strong></div>
      </div>
      <p className="status-note">Values come from backend timings. Total latency falls back to measured request time.</p>
    </Card>
  );
}
