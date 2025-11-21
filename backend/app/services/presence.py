"""
Presence service for collaborative sessions.

Manages user presence, cursor positions, and role assignments.
Uses Redis for persistence and real-time synchronization.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import random
import hashlib
import json
import redis.asyncio as aioredis


@dataclass
class UserPresence:
    """User presence data."""
    user_id: str
    session_id: str
    call_sign: str
    role: str  # operator, supervisor, observer
    color: str  # Hex color for cursor/pointer
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    last_active: str = ""
    socket_id: str = ""


class PresenceService:
    """Service for managing collaborative presence with Redis persistence."""

    # Predefined color palette for user cursors
    CURSOR_COLORS = [
        "#FF6B6B",  # Red
        "#4ECDC4",  # Teal
        "#45B7D1",  # Blue
        "#FFA07A",  # Light Salmon
        "#98D8C8",  # Mint
        "#F7DC6F",  # Yellow
        "#BB8FCE",  # Purple
        "#85C1E2",  # Sky Blue
        "#F8B195",  # Peach
        "#6C5CE7",  # Indigo
        "#00B894",  # Green
        "#FDCB6E",  # Mustard
        "#E84393",  # Pink
        "#74B9FF",  # Light Blue
        "#A29BFE",  # Lavender
    ]

    # Redis key prefixes
    PRESENCE_KEY_PREFIX = "presence:session"
    COLORS_KEY_PREFIX = "presence:colors:session"
    PRESENCE_INDEX_KEY = "presence:index"

    # Presence TTL in seconds (30 minutes of inactivity)
    PRESENCE_TTL = 1800

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            print(f"✓ PresenceService connected to Redis at {self.redis_url}")
        except Exception as e:
            print(f"✗ PresenceService failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            print("✓ PresenceService disconnected from Redis")

    async def join_session(
        self,
        session_id: str,
        user_id: str,
        socket_id: str,
        display_name: Optional[str] = None,
        role: str = "operator"
    ) -> UserPresence:
        """
        Add user to session.

        Args:
            session_id: Session identifier
            user_id: User identifier
            socket_id: Socket.IO socket ID
            display_name: Optional display name (generates call sign if not provided)
            role: User role (operator, supervisor, observer)

        Returns:
            User presence data
        """
        # Generate call sign if not provided
        call_sign = display_name or self._generate_call_sign(user_id)

        # Assign unique color
        color = await self._assign_color(session_id, user_id)

        presence = UserPresence(
            user_id=user_id,
            session_id=session_id,
            call_sign=call_sign,
            role=role,
            color=color,
            cursor_x=0.0,
            cursor_y=0.0,
            last_active=datetime.utcnow().isoformat(),
            socket_id=socket_id or ""
        )

        # Store in Redis
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_key = f"{presence_key}:{user_id}"

        # Convert to dict and ensure all values are strings for Redis
        presence_dict = asdict(presence)
        presence_dict = {k: str(v) if v is not None else "" for k, v in presence_dict.items()}

        await self.redis.hset(user_key, mapping=presence_dict)
        await self.redis.expire(user_key, self.PRESENCE_TTL)

        # Add to session index
        await self.redis.sadd(presence_key, user_id)

        # Add to global index for monitoring
        await self.redis.sadd(self.PRESENCE_INDEX_KEY, session_id)

        return presence

    async def leave_session(self, session_id: str, user_id: str) -> bool:
        """
        Remove user from session.

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            True if user was removed
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_key = f"{presence_key}:{user_id}"

        # Get user's color before removing
        user_data = await self.redis.hgetall(user_key)
        if user_data and "color" in user_data:
            # Free up the color
            colors_key = f"{self.COLORS_KEY_PREFIX}:{session_id}"
            await self.redis.srem(colors_key, user_data["color"])

        # Remove user from session
        await self.redis.delete(user_key)
        removed = await self.redis.srem(presence_key, user_id)

        # Clean up empty session
        session_size = await self.redis.scard(presence_key)
        if session_size == 0:
            await self.redis.delete(presence_key)
            colors_key = f"{self.COLORS_KEY_PREFIX}:{session_id}"
            await self.redis.delete(colors_key)
            await self.redis.srem(self.PRESENCE_INDEX_KEY, session_id)

        return removed > 0

    async def update_cursor(
        self,
        session_id: str,
        user_id: str,
        x: float,
        y: float
    ) -> Optional[UserPresence]:
        """
        Update user cursor position.

        Args:
            session_id: Session identifier
            user_id: User identifier
            x: Cursor X coordinate (0.0 to 1.0, normalized)
            y: Cursor Y coordinate (0.0 to 1.0, normalized)

        Returns:
            Updated presence or None if user not in session
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_key = f"{presence_key}:{user_id}"

        # Update cursor position and last active
        last_active = datetime.utcnow().isoformat()
        await self.redis.hmset(user_key, {
            "cursor_x": str(x),
            "cursor_y": str(y),
            "last_active": last_active
        })

        # Refresh TTL
        await self.redis.expire(user_key, self.PRESENCE_TTL)

        # Retrieve full presence data
        user_data = await self.redis.hgetall(user_key)
        if not user_data or "user_id" not in user_data:
            return None

        return UserPresence(
            user_id=user_data["user_id"],
            session_id=user_data["session_id"],
            call_sign=user_data["call_sign"],
            role=user_data["role"],
            color=user_data["color"],
            cursor_x=float(user_data["cursor_x"]),
            cursor_y=float(user_data["cursor_y"]),
            last_active=user_data["last_active"],
            socket_id=user_data["socket_id"]
        )

    async def get_session_users(self, session_id: str) -> List[UserPresence]:
        """
        Get all users in a session.

        Args:
            session_id: Session identifier

        Returns:
            List of user presences
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_ids = await self.redis.smembers(presence_key)

        if not user_ids:
            return []

        users = []
        for user_id in user_ids:
            user_key = f"{presence_key}:{user_id}"
            user_data = await self.redis.hgetall(user_key)
            if user_data:
                users.append(UserPresence(
                    user_id=user_data["user_id"],
                    session_id=user_data["session_id"],
                    call_sign=user_data["call_sign"],
                    role=user_data["role"],
                    color=user_data["color"],
                    cursor_x=float(user_data.get("cursor_x", 0)),
                    cursor_y=float(user_data.get("cursor_y", 0)),
                    last_active=user_data["last_active"],
                    socket_id=user_data["socket_id"]
                ))

        return users

    async def get_user_presence(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[UserPresence]:
        """
        Get specific user's presence.

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            User presence or None
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_key = f"{presence_key}:{user_id}"

        user_data = await self.redis.hgetall(user_key)
        if not user_data:
            return None

        return UserPresence(
            user_id=user_data["user_id"],
            session_id=user_data["session_id"],
            call_sign=user_data["call_sign"],
            role=user_data["role"],
            color=user_data["color"],
            cursor_x=float(user_data.get("cursor_x", 0)),
            cursor_y=float(user_data.get("cursor_y", 0)),
            last_active=user_data["last_active"],
            socket_id=user_data["socket_id"]
        )

    async def find_user_by_socket(self, socket_id: str) -> Optional[UserPresence]:
        """
        Find user by socket ID.

        Args:
            socket_id: Socket.IO socket ID

        Returns:
            User presence or None
        """
        # Get all sessions
        session_ids = await self.redis.smembers(self.PRESENCE_INDEX_KEY)

        for session_id in session_ids:
            presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
            user_ids = await self.redis.smembers(presence_key)

            for user_id in user_ids:
                user_key = f"{presence_key}:{user_id}"
                user_data = await self.redis.hgetall(user_key)
                if user_data and user_data.get("socket_id") == socket_id:
                    return UserPresence(
                        user_id=user_data["user_id"],
                        session_id=user_data["session_id"],
                        call_sign=user_data["call_sign"],
                        role=user_data["role"],
                        color=user_data["color"],
                        cursor_x=float(user_data.get("cursor_x", 0)),
                        cursor_y=float(user_data.get("cursor_y", 0)),
                        last_active=user_data["last_active"],
                        socket_id=user_data["socket_id"]
                    )

        return None

    async def _assign_color(self, session_id: str, user_id: str) -> str:
        """
        Assign unique color to user.

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            Hex color string
        """
        colors_key = f"{self.COLORS_KEY_PREFIX}:{session_id}"

        # Get used colors
        used_colors = await self.redis.smembers(colors_key)

        # Find available color
        available_colors = [
            color for color in self.CURSOR_COLORS
            if color not in used_colors
        ]

        if available_colors:
            # Use first available color
            color = available_colors[0]
        else:
            # All colors used, generate random color from user_id
            color = self._generate_color_from_id(user_id)

        # Store color
        await self.redis.sadd(colors_key, color)

        return color

    def _generate_color_from_id(self, user_id: str) -> str:
        """
        Generate consistent color from user ID.

        Args:
            user_id: User identifier

        Returns:
            Hex color string
        """
        # Hash user_id to get consistent color
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest()[:6], 16)

        # Generate vibrant color
        hue = hash_value % 360
        saturation = 70 + (hash_value % 30)  # 70-100%
        lightness = 50 + (hash_value % 20)   # 50-70%

        # Convert HSL to RGB (simplified)
        import colorsys
        r, g, b = colorsys.hls_to_rgb(hue / 360, lightness / 100, saturation / 100)

        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    def _generate_call_sign(self, user_id: str) -> str:
        """
        Generate call sign from user ID.

        Args:
            user_id: User identifier

        Returns:
            Call sign string
        """
        # Use last 4 characters of user_id
        suffix = user_id[-4:].upper()
        return f"callsign-{suffix}"

    async def get_all_sessions(self) -> List[str]:
        """
        Get list of all active session IDs.

        Returns:
            List of session IDs
        """
        return list(await self.redis.smembers(self.PRESENCE_INDEX_KEY))

    async def get_session_count(self, session_id: str) -> int:
        """
        Get count of users in a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of users in session
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        return await self.redis.scard(presence_key)

    async def heartbeat(self, session_id: str, user_id: str) -> bool:
        """
        Update user's last active timestamp to keep presence alive.

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            True if heartbeat was successful
        """
        presence_key = f"{self.PRESENCE_KEY_PREFIX}:{session_id}"
        user_key = f"{presence_key}:{user_id}"

        # Check if user exists
        exists = await self.redis.exists(user_key)
        if not exists:
            return False

        # Update last active
        last_active = datetime.utcnow().isoformat()
        await self.redis.hset(user_key, "last_active", last_active)

        # Refresh TTL
        await self.redis.expire(user_key, self.PRESENCE_TTL)

        return True

    def to_dict(self, presence: UserPresence) -> dict:
        """Convert presence to dictionary."""
        return asdict(presence)


# Singleton instance
_presence_service: Optional[PresenceService] = None


def get_presence_service(redis_url: Optional[str] = None) -> PresenceService:
    """
    Get or create presence service singleton.

    Args:
        redis_url: Optional Redis URL (uses default if not provided)

    Returns:
        PresenceService instance
    """
    global _presence_service
    if _presence_service is None:
        from app.core.config import get_settings
        settings = get_settings()
        _presence_service = PresenceService(redis_url or settings.redis_url)
    return _presence_service
