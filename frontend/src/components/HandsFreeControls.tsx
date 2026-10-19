import { MicOff, VolumeX } from "lucide-react";
import { useVoice } from "../context/VoiceContext";
import { Card } from "./ui/card";

export function HandsFreeControls() {
  const {
    handsFreeStatus, handsFreeMuted, clapEnabled, clapThreshold, twoClaps, silenceMs,
    setClapEnabled, setClapThreshold, setTwoClaps, setSilenceMs,
    startHandsFree, stopHandsFree, toggleHandsFreeMute, stopSpeaking, phase,
  } = useVoice();
  const active = handsFreeStatus !== "off" && handsFreeStatus !== "error";
  return <Card className="hands-free-card">
    <div className="hands-free-heading"><div><p className="overline">Hands-free</p><h2>Voice activation</h2></div><span className="hands-free-status" role="status" aria-label={`Hands-free ${handsFreeStatus}`}>{handsFreeStatus.replaceAll("-", " ")}</span></div>
    <p className="hands-free-note">“Carrot” requires a trained local wake-word model and is not active yet. Clap activation works while this page stays open.</p>
    <div className="hands-free-actions">
      <button type="button" className="hands-free-primary" onClick={() => active ? stopHandsFree() : void startHandsFree()}>{active ? "Stop hands-free" : "Enable hands-free"}</button>
      <button type="button" onClick={toggleHandsFreeMute} disabled={!active} aria-label={handsFreeMuted ? "Unmute microphone" : "Mute microphone"}><MicOff />{handsFreeMuted ? "Unmute" : "Mute"}</button>
      <button type="button" onClick={stopSpeaking} disabled={phase !== "speaking"}><VolumeX />Stop speech</button>
    </div>
    <div className="hands-free-options">
      <label><input type="checkbox" checked={clapEnabled} onChange={(event) => setClapEnabled(event.target.checked)} /> Clap activation</label>
      <label><input type="checkbox" checked={twoClaps} onChange={(event) => setTwoClaps(event.target.checked)} /> Require two claps</label>
      <label>Clap sensitivity <input aria-label="Clap sensitivity" type="range" min="0.04" max="0.2" step="0.01" value={clapThreshold} onChange={(event) => setClapThreshold(Number(event.target.value))} /></label>
      <label>End after silence <select aria-label="Silence duration" value={silenceMs} onChange={(event) => setSilenceMs(Number(event.target.value))}><option value="600">0.6 s</option><option value="900">0.9 s</option><option value="1400">1.4 s</option></select></label>
    </div>
  </Card>;
}
