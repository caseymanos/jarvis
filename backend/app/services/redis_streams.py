"""
Redis Streams service for real-time synchronization.

Handles broadcasting of:
- Transcript updates
- Agent state changes (idle/listening/thinking/speaking)
- Session events
- Backend health metrics
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()


class RedisStreamsService:
    """Service for managing Redis Streams for real-time updates."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._connection_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Establish connection to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            print(f"✓ Connected to Redis at {settings.redis_url}")
        except Exception as e:
            print(f"✗ Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            print("✓ Disconnected from Redis")

    async def publish_transcript_update(
        self,
        session_id: str,
        transcript_chunk: Dict[str, Any]
    ) -> str:
        """
        Publish a transcript update to the stream.

        Args:
            session_id: Unique session identifier
            transcript_chunk: Transcript data with speaker, text, timestamp

        Returns:
            Message ID from Redis stream
        """
        stream_key = f"session:{session_id}:transcripts"

        data = {
            "type": "transcript_update",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "chunk_id": transcript_chunk.get("id", ""),
            "speaker": transcript_chunk.get("speaker", "user"),
            "text": transcript_chunk.get("text", ""),
            "is_final": str(transcript_chunk.get("is_final", True)),
        }

        message_id = await self.redis.xadd(
            stream_key,
            data,
            maxlen=settings.redis_stream_maxlen
        )

        return message_id

    async def publish_agent_state_update(
        self,
        session_id: str,
        state: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish agent state change to the stream.

        Args:
            session_id: Unique session identifier
            state: Agent state (idle/listening/thinking/speaking)
            metadata: Optional additional data

        Returns:
            Message ID from Redis stream
        """
        stream_key = f"session:{session_id}:agent_state"

        data = {
            "type": "agent_state_update",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "state": state,
            "metadata": json.dumps(metadata or {}),
        }

        message_id = await self.redis.xadd(
            stream_key,
            data,
            maxlen=settings.redis_stream_maxlen
        )

        return message_id

    async def publish_session_event(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Publish session event to the stream.

        Args:
            session_id: Unique session identifier
            event_type: Event type (start/stop/interrupt/error)
            data: Event data

        Returns:
            Message ID from Redis stream
        """
        stream_key = f"session:{session_id}:events"

        event_data = {
            "type": "session_event",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": json.dumps(data),
        }

        message_id = await self.redis.xadd(
            stream_key,
            event_data,
            maxlen=settings.redis_stream_maxlen
        )

        return message_id

    async def publish_health_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Publish backend health metric to the stream.

        Args:
            metric_name: Name of the metric (latency_ms, error_rate, etc.)
            value: Metric value
            labels: Optional metric labels

        Returns:
            Message ID from Redis stream
        """
        stream_key = "backend:health_metrics"

        data = {
            "type": "health_metric",
            "timestamp": datetime.utcnow().isoformat(),
            "metric_name": metric_name,
            "value": str(value),
            "labels": json.dumps(labels or {}),
        }

        message_id = await self.redis.xadd(
            stream_key,
            data,
            maxlen=settings.redis_stream_maxlen
        )

        return message_id

    async def read_stream(
        self,
        stream_key: str,
        last_id: str = "0-0",
        count: int = 100,
        block_ms: Optional[int] = None
    ) -> List[tuple]:
        """
        Read messages from a stream.

        Args:
            stream_key: Redis stream key
            last_id: Last message ID received (use "0-0" for all, "$" for new only)
            count: Maximum number of messages to read
            block_ms: Optional blocking timeout in milliseconds

        Returns:
            List of (message_id, data) tuples
        """
        try:
            if block_ms is not None:
                # Blocking read for real-time updates
                result = await self.redis.xread(
                    {stream_key: last_id},
                    count=count,
                    block=block_ms
                )
            else:
                # Non-blocking read
                result = await self.redis.xread(
                    {stream_key: last_id},
                    count=count
                )

            # Parse results
            messages = []
            if result:
                for stream_name, stream_messages in result:
                    for message_id, data in stream_messages:
                        messages.append((message_id, data))

            return messages
        except Exception as e:
            print(f"Error reading stream {stream_key}: {e}")
            return []

    async def get_stream_info(self, stream_key: str) -> Dict[str, Any]:
        """
        Get information about a stream.

        Args:
            stream_key: Redis stream key

        Returns:
            Stream info dictionary
        """
        try:
            info = await self.redis.xinfo_stream(stream_key)
            return info
        except Exception as e:
            print(f"Error getting stream info for {stream_key}: {e}")
            return {}

    async def create_consumer_group(
        self,
        stream_key: str,
        group_name: str,
        start_id: str = "0-0"
    ):
        """
        Create a consumer group for stream processing.

        Args:
            stream_key: Redis stream key
            group_name: Name of consumer group
            start_id: Starting message ID ("0-0" for all, "$" for new only)
        """
        try:
            await self.redis.xgroup_create(
                stream_key,
                group_name,
                id=start_id,
                mkstream=True
            )
            print(f"✓ Created consumer group '{group_name}' for {stream_key}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                print(f"Consumer group '{group_name}' already exists for {stream_key}")
            else:
                raise

    async def read_from_consumer_group(
        self,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: Optional[int] = None
    ) -> List[tuple]:
        """
        Read messages from a stream using a consumer group.

        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            consumer_name: Unique consumer identifier
            count: Maximum number of messages to read
            block_ms: Optional blocking timeout in milliseconds

        Returns:
            List of (message_id, data) tuples
        """
        try:
            result = await self.redis.xreadgroup(
                group_name,
                consumer_name,
                {stream_key: ">"},
                count=count,
                block=block_ms
            )

            messages = []
            if result:
                for stream_name, stream_messages in result:
                    for message_id, data in stream_messages:
                        messages.append((message_id, data))

            return messages
        except Exception as e:
            print(f"Error reading from consumer group: {e}")
            return []

    async def acknowledge_message(
        self,
        stream_key: str,
        group_name: str,
        message_id: str
    ):
        """
        Acknowledge a message has been processed.

        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            message_id: Message ID to acknowledge
        """
        try:
            await self.redis.xack(stream_key, group_name, message_id)
        except Exception as e:
            print(f"Error acknowledging message {message_id}: {e}")


# Singleton instance
_redis_service: Optional[RedisStreamsService] = None


def get_redis_service() -> RedisStreamsService:
    """Get or create the Redis streams service singleton."""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisStreamsService()
    return _redis_service
