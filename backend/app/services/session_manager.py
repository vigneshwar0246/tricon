"""Bounded in-memory conversation sessions with per-session serialization."""

import asyncio
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Literal
from uuid import uuid4

from app.core.config import get_settings


@dataclass
class ConversationMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class ConversationSession:
    session_id: str
    messages: list[ConversationMessage] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active_requests: int = 0
    deleting: bool = False


class SessionCapacityError(RuntimeError):
    pass


class SessionManager:
    """Stores only recent turns in process memory; sessions reset on restart."""

    def __init__(self, max_turns: int | None = None, max_sessions: int | None = None) -> None:
        settings = get_settings()
        self.max_turns = max_turns or settings.session_max_turns
        self.max_sessions = max_sessions or settings.session_max_count
        self._sessions: OrderedDict[str, ConversationSession] = OrderedDict()
        self._index_lock = asyncio.Lock()

    async def get_or_create(self, session_id: str | None = None) -> ConversationSession:
        requested_id = session_id or str(uuid4())
        async with self._index_lock:
            return self._get_or_create_locked(requested_id)

    def _get_or_create_locked(self, requested_id: str) -> ConversationSession:
        session = self._sessions.get(requested_id)
        if session is not None and session.deleting:
            raise SessionCapacityError("This conversation is being cleared. Start a new conversation.")
        if session is None:
            if len(self._sessions) >= self.max_sessions:
                victim_id = next((
                    session_id for session_id, candidate in self._sessions.items()
                    if candidate.active_requests == 0 and not candidate.lock.locked()
                ), None)
                if victim_id is None:
                    raise SessionCapacityError("All conversation slots are busy. Try again shortly.")
                self._sessions.pop(victim_id)
            session = ConversationSession(session_id=requested_id)
            self._sessions[requested_id] = session
        self._sessions.move_to_end(requested_id)
        return session

    @asynccontextmanager
    async def conversation(self, session_id: str | None = None) -> AsyncIterator[ConversationSession]:
        """Reserve and serialize a turn without evicting sessions with queued requests."""
        requested_id = session_id or str(uuid4())
        async with self._index_lock:
            session = self._get_or_create_locked(requested_id)
            session.active_requests += 1
        try:
            await session.lock.acquire()
        except BaseException:
            async with self._index_lock:
                session.active_requests -= 1
            raise
        try:
            yield session
        finally:
            session.lock.release()
            async with self._index_lock:
                session.active_requests -= 1

    @asynccontextmanager
    async def locked(self, session: ConversationSession) -> AsyncIterator[ConversationSession]:
        async with session.lock:
            yield session

    def history(self, session: ConversationSession) -> list[dict[str, str]]:
        return [{"role": message.role, "content": message.content} for message in session.messages]

    def add_exchange(self, session: ConversationSession, user_text: str, assistant_text: str) -> None:
        session.messages.extend([
            ConversationMessage(role="user", content=user_text),
            ConversationMessage(role="assistant", content=assistant_text),
        ])
        max_messages = self.max_turns * 2
        if len(session.messages) > max_messages:
            session.messages = session.messages[-max_messages:]
        session.updated_at = datetime.now(timezone.utc)

    async def delete(self, session_id: str) -> bool:
        async with self._index_lock:
            session = self._sessions.get(session_id)
            if session is None or session.deleting:
                return False
            session.deleting = True
        try:
            while True:
                await session.lock.acquire()
                async with self._index_lock:
                    if session.active_requests == 0 and self._sessions.get(session_id) is session:
                        self._sessions.pop(session_id, None)
                        session.lock.release()
                        return True
                session.lock.release()
        except BaseException:
            async with self._index_lock:
                if self._sessions.get(session_id) is session:
                    session.deleting = False
            raise

    async def list_sessions(self) -> list[tuple[str, int, datetime]]:
        async with self._index_lock:
            return [(item.session_id, len(item.messages), item.updated_at) for item in reversed(self._sessions.values())]


session_manager = SessionManager()
