"""
Session State Persistence Service

Manages voice session state with:
- Redis for low-latency reads/writes (in-memory cache)
- Postgres for durable persistence
- Automatic state synchronization
- Multi-device support
- Offline queue replay
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.session import VoiceSession, TranscriptChunk, SessionSnapshot
from app.core.config import settings


class AgentState(str, Enum):
    """Agent states during voice session"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass
class SessionState:
    """Complete session state for persistence"""
    session_id: str
    user_id: str
    agent_state: AgentState
    is_active: bool
    last_activity: datetime
    transcript_count: int
    metadata: Dict[str, Any]
    device_ids: List[str]  # For multi-device support

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_state": self.agent_state.value,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat(),
            "transcript_count": self.transcript_count,
            "metadata": self.metadata,
            "device_ids": self.device_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create from dict"""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            agent_state=AgentState(data["agent_state"]),
            is_active=data["is_active"],
            last_activity=datetime.fromisoformat(data["last_activity"]),
            transcript_count=data["transcript_count"],
            metadata=data.get("metadata", {}),
            device_ids=data.get("device_ids", []),
        )


class SessionStateService:
    """
    Manages session state with dual-layer persistence:
    - Redis: Fast in-memory cache (TTL-based)
    - Postgres: Durable storage
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        self.state_ttl = 3600  # 1 hour TTL for active sessions
        self.snapshot_interval = 60  # Snapshot to DB every 60 seconds

    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    def _get_state_key(self, session_id: str) -> str:
        """Generate Redis key for session state"""
        return f"session:state:{session_id}"

    def _get_queue_key(self, session_id: str) -> str:
        """Generate Redis key for offline queue"""
        return f"session:queue:{session_id}"

    async def create_session(
        self,
        db: AsyncSession,
        user_id: str,
        device_id: str,
        metadata: Dict[str, Any] = None
    ) -> SessionState:
        """
        Create a new voice session

        Args:
            db: Database session
            user_id: User ID
            device_id: Device identifier
            metadata: Optional session metadata

        Returns:
            SessionState object
        """
        await self.connect()

        # Create in Postgres
        session = VoiceSession(
            user_id=user_id,
            is_active=True,
            metadata=metadata or {}
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Create state object
        state = SessionState(
            session_id=session.id,
            user_id=user_id,
            agent_state=AgentState.IDLE,
            is_active=True,
            last_activity=datetime.utcnow(),
            transcript_count=0,
            metadata=metadata or {},
            device_ids=[device_id]
        )

        # Cache in Redis
        await self._save_to_redis(state)

        return state

    async def get_session_state(
        self,
        session_id: str,
        db: AsyncSession = None
    ) -> Optional[SessionState]:
        """
        Get session state (Redis first, fallback to Postgres)

        Args:
            session_id: Session ID
            db: Database session (optional, for fallback)

        Returns:
            SessionState or None
        """
        await self.connect()

        # Try Redis first (low latency)
        state = await self._load_from_redis(session_id)
        if state:
            return state

        # Fallback to Postgres
        if db:
            state = await self._load_from_db(session_id, db)
            if state:
                # Restore to Redis
                await self._save_to_redis(state)
            return state

        return None

    async def update_state(
        self,
        session_id: str,
        agent_state: Optional[AgentState] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> Optional[SessionState]:
        """
        Update session state

        Args:
            session_id: Session ID
            agent_state: New agent state (optional)
            metadata: Metadata updates (optional)
            db: Database session (for persistence)

        Returns:
            Updated SessionState
        """
        await self.connect()

        # Get current state
        state = await self.get_session_state(session_id, db)
        if not state:
            return None

        # Update fields
        if agent_state:
            state.agent_state = agent_state
        if metadata:
            state.metadata.update(metadata)
        state.last_activity = datetime.utcnow()

        # Save to Redis (fast)
        await self._save_to_redis(state)

        # Async save to Postgres (durable)
        if db:
            asyncio.create_task(self._save_snapshot_to_db(state, db))

        return state

    async def add_device(
        self,
        session_id: str,
        device_id: str,
        db: AsyncSession = None
    ) -> Optional[SessionState]:
        """
        Add a device to session (multi-device support)

        Args:
            session_id: Session ID
            device_id: Device identifier
            db: Database session

        Returns:
            Updated SessionState
        """
        await self.connect()

        state = await self.get_session_state(session_id, db)
        if not state:
            return None

        if device_id not in state.device_ids:
            state.device_ids.append(device_id)
            await self._save_to_redis(state)

            if db:
                asyncio.create_task(self._save_snapshot_to_db(state, db))

        return state

    async def remove_device(
        self,
        session_id: str,
        device_id: str,
        db: AsyncSession = None
    ) -> Optional[SessionState]:
        """
        Remove a device from session

        Args:
            session_id: Session ID
            device_id: Device identifier
            db: Database session

        Returns:
            Updated SessionState
        """
        await self.connect()

        state = await self.get_session_state(session_id, db)
        if not state:
            return None

        if device_id in state.device_ids:
            state.device_ids.remove(device_id)

            # If no devices left, mark session as inactive
            if not state.device_ids:
                state.is_active = False

            await self._save_to_redis(state)

            if db:
                asyncio.create_task(self._save_snapshot_to_db(state, db))

        return state

    async def queue_offline_action(
        self,
        session_id: str,
        action: Dict[str, Any]
    ):
        """
        Queue an action for offline replay

        Args:
            session_id: Session ID
            action: Action data (type, payload, timestamp)
        """
        await self.connect()

        queue_key = self._get_queue_key(session_id)
        action["queued_at"] = datetime.utcnow().isoformat()

        await self.redis_client.rpush(
            queue_key,
            json.dumps(action)
        )
        await self.redis_client.expire(queue_key, 86400)  # 24h TTL

    async def replay_offline_queue(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Replay offline queue and clear it

        Args:
            session_id: Session ID

        Returns:
            List of queued actions
        """
        await self.connect()

        queue_key = self._get_queue_key(session_id)

        # Get all queued items
        queue_data = await self.redis_client.lrange(queue_key, 0, -1)
        actions = [json.loads(item) for item in queue_data]

        # Clear the queue
        await self.redis_client.delete(queue_key)

        return actions

    async def end_session(
        self,
        session_id: str,
        db: AsyncSession
    ):
        """
        End a session and persist final state

        Args:
            session_id: Session ID
            db: Database session
        """
        await self.connect()

        # Get final state
        state = await self.get_session_state(session_id, db)
        if not state:
            return

        # Mark as inactive
        state.is_active = False
        state.last_activity = datetime.utcnow()

        # Save final snapshot to DB
        await self._save_snapshot_to_db(state, db)

        # Update Postgres session
        await db.execute(
            update(VoiceSession)
            .where(VoiceSession.id == session_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        await db.commit()

        # Remove from Redis after a grace period (for reconnects)
        await self.redis_client.expire(
            self._get_state_key(session_id),
            300  # 5 minutes
        )

    async def _save_to_redis(self, state: SessionState):
        """Save state to Redis with TTL"""
        key = self._get_state_key(state.session_id)
        await self.redis_client.set(
            key,
            json.dumps(state.to_dict()),
            ex=self.state_ttl
        )

    async def _load_from_redis(self, session_id: str) -> Optional[SessionState]:
        """Load state from Redis"""
        key = self._get_state_key(session_id)
        data = await self.redis_client.get(key)

        if data:
            return SessionState.from_dict(json.loads(data))
        return None

    async def _load_from_db(
        self,
        session_id: str,
        db: AsyncSession
    ) -> Optional[SessionState]:
        """Load state from Postgres (latest snapshot)"""
        # Get session
        result = await db.execute(
            select(VoiceSession)
            .where(VoiceSession.id == session_id)
            .options(selectinload(VoiceSession.snapshots))
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Get latest snapshot
        if session.snapshots:
            latest = max(session.snapshots, key=lambda s: s.created_at)
            return SessionState(
                session_id=session.id,
                user_id=session.user_id,
                agent_state=AgentState(latest.agent_state),
                is_active=session.is_active,
                last_activity=session.updated_at,
                transcript_count=latest.transcript_count,
                metadata=latest.metadata or {},
                device_ids=latest.device_ids or []
            )

        # No snapshot, create fresh state
        return SessionState(
            session_id=session.id,
            user_id=session.user_id,
            agent_state=AgentState.IDLE,
            is_active=session.is_active,
            last_activity=session.updated_at,
            transcript_count=0,
            metadata=session.metadata or {},
            device_ids=[]
        )

    async def _save_snapshot_to_db(self, state: SessionState, db: AsyncSession):
        """Save state snapshot to Postgres"""
        snapshot = SessionSnapshot(
            session_id=state.session_id,
            agent_state=state.agent_state.value,
            transcript_count=state.transcript_count,
            metadata=state.metadata,
            device_ids=state.device_ids
        )
        db.add(snapshot)
        await db.commit()


# Singleton instance
session_state_service = SessionStateService()
