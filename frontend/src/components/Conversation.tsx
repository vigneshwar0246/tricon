import { Bot, Mic, Pause, Play, Send, Sparkles, Trash2, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useVoice } from "../context/VoiceContext";
import type { Message } from "../types";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

function MessageAudio({ url }: { url: string }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  useEffect(() => () => audio.current?.pause(), []);
  const toggle = () => {
    audio.current ??= new Audio(url);
    audio.current.onended = () => setPlaying(false);
    if (audio.current.paused) { void audio.current.play(); setPlaying(true); }
    else { audio.current.pause(); setPlaying(false); }
  };
  return <button className="audio-control" onClick={toggle}>{playing ? <Pause /> : <Play />}<span>{playing ? "Pause response" : "Play response"}</span></button>;
}

function MessageBubble({ message }: { message: Message }) {
  const assistant = message.role === "assistant";
  return (
    <article className={`message ${message.role}`}>
      <span className="message-avatar">{assistant ? <Bot /> : <UserRound />}</span>
      <div className="message-content"><span className="message-label">{assistant ? "AI Voice Assistant" : "You"}</span><p>{message.content}</p>{assistant && message.audioUrl && <MessageAudio url={message.audioUrl} />}</div>
    </article>
  );
}

export function Conversation({ expanded = false }: { expanded?: boolean }) {
  const { messages, phase, error, submitText, toggleRecording, clearConversation } = useVoice();
  const [draft, setDraft] = useState("");
  const feed = useRef<HTMLDivElement>(null);
  useEffect(() => { feed.current?.scrollTo({ top: feed.current.scrollHeight, behavior: "smooth" }); }, [messages, phase]);
  const submit = (event: React.FormEvent) => { event.preventDefault(); if (draft.trim()) { void submitText(draft); setDraft(""); } };
  return (
    <Card className={`conversation ${expanded ? "conversation-expanded" : ""}`}>
      <div className="conversation-header"><div><p className="overline">Conversation</p><h2>{expanded ? "Conversation workspace" : "Continue in your own words"}</h2></div><Button variant="ghost" onClick={clearConversation} disabled={!messages.length}><Trash2 />Clear</Button></div>
      <div className="message-feed" ref={feed} aria-live="polite">
        {!messages.length && <div className="conversation-empty"><span><Sparkles /></span><strong>No messages yet</strong><p>Speak or type a question to start a local conversation.</p></div>}
        {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
        {phase === "processing" && <div className="thinking-row" role="status"><span /><span /><span /><p>Processing with local models</p></div>}
      </div>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <form className="composer" onSubmit={submit}>
        <label htmlFor={expanded ? "message-expanded" : "message"}>Message</label>
        <div className="composer-field">
          <input id={expanded ? "message-expanded" : "message"} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask me anything" disabled={phase === "processing"} />
          <button type="button" className={`composer-icon ${phase === "listening" ? "recording" : ""}`} onClick={() => void toggleRecording()} aria-label={phase === "listening" ? "Stop listening" : "Start listening"}><Mic /></button>
          <button type="submit" className="composer-send" disabled={!draft.trim() || phase === "processing"} aria-label="Send message"><Send /></button>
        </div>
      </form>
    </Card>
  );
}
