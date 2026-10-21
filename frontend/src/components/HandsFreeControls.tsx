import { MicOff, VolumeX } from "lucide-react";
import { useVoice } from "../context/VoiceContext";
import { Card } from "./ui/card";

export function HandsFreeControls() {
  const {
    handsFreeStatus, handsFreeMuted, silenceMs, setSilenceMs,
    startHandsFree, stopHandsFree, toggleHandsFreeMute, stopSpeaking, phase,
    bargeInEnabled, setBargeInEnabled,
  } = useVoice();
  const active = handsFreeStatus !== "off" && handsFreeStatus !== "error";
  return <Card className="hands-free-card">
    <div className="hands-free-heading"><div><p className="overline">Hands-free</p><h2>Voice activation</h2></div><span className="hands-free-status" role="status" aria-label={`Hands-free ${handsFreeStatus}`}>{handsFreeStatus.replaceAll("-", " ")}</span></div>
    <p className="hands-free-note">Enable hands-free once and start speaking naturally. Pauses send your turn; the assistant answers aloud, then listens again. The “Carrot” wake word is not available until its local model is trained.</p>
    <div className="hands-free-actions">
      <button type="button" className="hands-free-primary" onClick={() => active ? stopHandsFree() : void startHandsFree()}>{active ? "Stop hands-free" : "Enable hands-free"}</button>
      <button type="button" onClick={toggleHandsFreeMute} disabled={!active} aria-label={handsFreeMuted ? "Unmute microphone" : "Mute microphone"}><MicOff />{handsFreeMuted ? "Unmute" : "Mute"}</button>
      <button type="button" onClick={stopSpeaking} disabled={phase !== "speaking"}><VolumeX />Stop speech</button>
    </div>
    <div className="hands-free-options">
      <label>End after silence <select aria-label="Silence duration" value={silenceMs} onChange={(event) => setSilenceMs(Number(event.target.value))}><option value="600">0.6 s</option><option value="900">0.9 s</option><option value="1400">1.4 s</option></select></label>
      <label><input type="checkbox" checked={bargeInEnabled} onChange={(event) => setBargeInEnabled(event.target.checked)} /> Allow interruption while speaking</label>
    </div>
  </Card>;
}
