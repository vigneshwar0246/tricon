"""Explicit, non-shell voice commands. Everything else goes to the local LLM."""

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Command:
    response: str
    action: str | None = None


def route_command(transcript: str, last_response: str | None = None, now: datetime | None = None) -> Command | None:
    text = re.sub(r"[^a-z0-9 ]", "", transcript.lower()).strip()
    if text in {"stop listening", "stop voice listening", "stop hands free", "stop handsfree"}:
        return Command("Hands-free listening stopped.", "stop_listening")
    if text in {"clear conversation", "clear the conversation", "start a new conversation"}:
        return Command("Conversation cleared. We can start fresh.", "clear_conversation")
    if text in {"what time is it", "tell me the time", "current time"}:
        local_time = (now or datetime.now().astimezone()).strftime("%I:%M %p").lstrip("0")
        return Command(f"The current time is {local_time}.")
    if text in {"repeat that", "repeat your last response", "say that again"}:
        return Command(last_response or "There is no earlier response to repeat.")
    if re.match(r"^(open|launch|run|execute|delete|remove)\b", text):
        return Command("That system action is not supported. I cannot run commands or change files.")
    return None
