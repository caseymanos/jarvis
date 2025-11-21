"""
API endpoints for Redis Streams consumption.

Provides SSE (Server-Sent Events) endpoints for real-time updates.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
from app.services.redis_streams import get_redis_service

router = APIRouter(prefix="/streams", tags=["streams"])


async def stream_generator(
    stream_key: str,
    last_id: str = "$"
) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream from Redis stream.

    Args:
        stream_key: Redis stream key to subscribe to
        last_id: Starting message ID ("$" for new messages only)

    Yields:
        SSE-formatted messages
    """
    redis_service = get_redis_service()
    current_id = last_id

    try:
        while True:
            # Block for up to 5 seconds waiting for new messages
            messages = await redis_service.read_stream(
                stream_key=stream_key,
                last_id=current_id,
                count=10,
                block_ms=5000
            )

            if messages:
                for message_id, data in messages:
                    # Format as SSE
                    event_data = {
                        "id": message_id,
                        "data": data
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    current_id = message_id
            else:
                # Send keepalive
                yield ": keepalive\n\n"

            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        print(f"Stream cancelled for {stream_key}")
    except Exception as e:
        print(f"Error in stream generator: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.get("/session/{session_id}/transcripts")
async def stream_transcripts(session_id: str):
    """
    Stream transcript updates for a session via SSE.

    Args:
        session_id: Session identifier

    Returns:
        SSE stream of transcript updates
    """
    stream_key = f"session:{session_id}:transcripts"

    return StreamingResponse(
        stream_generator(stream_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/session/{session_id}/agent-state")
async def stream_agent_state(session_id: str):
    """
    Stream agent state updates for a session via SSE.

    Args:
        session_id: Session identifier

    Returns:
        SSE stream of agent state changes
    """
    stream_key = f"session:{session_id}:agent_state"

    return StreamingResponse(
        stream_generator(stream_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}/events")
async def stream_session_events(session_id: str):
    """
    Stream session events via SSE.

    Args:
        session_id: Session identifier

    Returns:
        SSE stream of session events
    """
    stream_key = f"session:{session_id}:events"

    return StreamingResponse(
        stream_generator(stream_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health-metrics")
async def stream_health_metrics():
    """
    Stream backend health metrics via SSE.

    Returns:
        SSE stream of health metrics
    """
    stream_key = "backend:health_metrics"

    return StreamingResponse(
        stream_generator(stream_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}/history/transcripts")
async def get_transcript_history(
    session_id: str,
    count: int = 100
):
    """
    Get historical transcript messages for a session.

    Args:
        session_id: Session identifier
        count: Number of messages to retrieve (max 1000)

    Returns:
        List of transcript messages
    """
    if count > 1000:
        raise HTTPException(status_code=400, detail="Count must be <= 1000")

    redis_service = get_redis_service()
    stream_key = f"session:{session_id}:transcripts"

    messages = await redis_service.read_stream(
        stream_key=stream_key,
        last_id="0-0",  # From beginning
        count=count
    )

    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": [
            {
                "id": msg_id,
                "data": data
            }
            for msg_id, data in messages
        ]
    }


@router.get("/session/{session_id}/info")
async def get_session_stream_info(session_id: str):
    """
    Get information about session streams.

    Args:
        session_id: Session identifier

    Returns:
        Stream info for all session streams
    """
    redis_service = get_redis_service()

    stream_keys = [
        f"session:{session_id}:transcripts",
        f"session:{session_id}:agent_state",
        f"session:{session_id}:events"
    ]

    info = {}
    for key in stream_keys:
        stream_info = await redis_service.get_stream_info(key)
        if stream_info:
            info[key] = {
                "length": stream_info.get("length", 0),
                "first_entry": stream_info.get("first-entry"),
                "last_entry": stream_info.get("last-entry")
            }

    return {
        "session_id": session_id,
        "streams": info
    }
