"""
Session State API Endpoints

Provides REST API for session state management:
- Create/restore sessions
- Update state
- Multi-device support
- Offline queue replay
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.services.session_state import (
    session_state_service,
    SessionState,
    AgentState
)

router = APIRouter(prefix="/session-state", tags=["session-state"])


# Request/Response Models
class CreateSessionRequest(BaseModel):
    user_id: str
    device_id: str
    metadata: Optional[Dict[str, Any]] = None


class SessionStateResponse(BaseModel):
    session_id: str
    user_id: str
    agent_state: str
    is_active: bool
    last_activity: datetime
    transcript_count: int
    metadata: Dict[str, Any]
    device_ids: List[str]


class UpdateStateRequest(BaseModel):
    agent_state: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AddDeviceRequest(BaseModel):
    device_id: str


class QueueActionRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any]


# Endpoints

@router.post("/create", response_model=SessionStateResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new voice session

    Creates session in both Postgres (durable) and Redis (fast access)
    """
    try:
        state = await session_state_service.create_session(
            db=db,
            user_id=request.user_id,
            device_id=request.device_id,
            metadata=request.metadata
        )

        return SessionStateResponse(
            session_id=state.session_id,
            user_id=state.user_id,
            agent_state=state.agent_state.value,
            is_active=state.is_active,
            last_activity=state.last_activity,
            transcript_count=state.transcript_count,
            metadata=state.metadata,
            device_ids=state.device_ids
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session_state(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get session state

    Tries Redis first (low latency), falls back to Postgres if needed
    """
    state = await session_state_service.get_session_state(session_id, db)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return SessionStateResponse(
        session_id=state.session_id,
        user_id=state.user_id,
        agent_state=state.agent_state.value,
        is_active=state.is_active,
        last_activity=state.last_activity,
        transcript_count=state.transcript_count,
        metadata=state.metadata,
        device_ids=state.device_ids
    )


@router.put("/{session_id}", response_model=SessionStateResponse)
async def update_session_state(
    session_id: str,
    request: UpdateStateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update session state

    Updates Redis immediately, snapshots to Postgres asynchronously
    """
    try:
        agent_state = None
        if request.agent_state:
            agent_state = AgentState(request.agent_state)

        state = await session_state_service.update_state(
            session_id=session_id,
            agent_state=agent_state,
            metadata=request.metadata,
            db=db
        )

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return SessionStateResponse(
            session_id=state.session_id,
            user_id=state.user_id,
            agent_state=state.agent_state.value,
            is_active=state.is_active,
            last_activity=state.last_activity,
            transcript_count=state.transcript_count,
            metadata=state.metadata,
            device_ids=state.device_ids
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent_state: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


@router.post("/{session_id}/devices", response_model=SessionStateResponse)
async def add_device_to_session(
    session_id: str,
    request: AddDeviceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a device to session (multi-device support)

    Allows the same session to be accessed from multiple devices
    """
    state = await session_state_service.add_device(
        session_id=session_id,
        device_id=request.device_id,
        db=db
    )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return SessionStateResponse(
        session_id=state.session_id,
        user_id=state.user_id,
        agent_state=state.agent_state.value,
        is_active=state.is_active,
        last_activity=state.last_activity,
        transcript_count=state.transcript_count,
        metadata=state.metadata,
        device_ids=state.device_ids
    )


@router.delete("/{session_id}/devices/{device_id}", response_model=SessionStateResponse)
async def remove_device_from_session(
    session_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a device from session

    Session becomes inactive when last device is removed
    """
    state = await session_state_service.remove_device(
        session_id=session_id,
        device_id=device_id,
        db=db
    )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return SessionStateResponse(
        session_id=state.session_id,
        user_id=state.user_id,
        agent_state=state.agent_state.value,
        is_active=state.is_active,
        last_activity=state.last_activity,
        transcript_count=state.transcript_count,
        metadata=state.metadata,
        device_ids=state.device_ids
    )


@router.post("/{session_id}/queue", status_code=status.HTTP_201_CREATED)
async def queue_offline_action(
    session_id: str,
    request: QueueActionRequest
):
    """
    Queue an action for offline replay

    Used when client is offline - actions are queued and replayed on reconnect
    """
    try:
        await session_state_service.queue_offline_action(
            session_id=session_id,
            action={
                "type": request.action_type,
                "payload": request.payload,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        return {"status": "queued", "session_id": session_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue action: {str(e)}"
        )


@router.post("/{session_id}/replay", response_model=List[Dict[str, Any]])
async def replay_offline_queue(session_id: str):
    """
    Replay and clear offline queue

    Returns all queued actions and clears the queue
    """
    try:
        actions = await session_state_service.replay_offline_queue(session_id)
        return actions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replay queue: {str(e)}"
        )


@router.delete("/{session_id}")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    End a session

    Persists final state to Postgres and marks as inactive
    """
    try:
        await session_state_service.end_session(session_id, db)
        return {"status": "ended", "session_id": session_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.get("/{session_id}/health")
async def session_health_check(session_id: str):
    """
    Check if session state service is healthy

    Used for monitoring and debugging
    """
    try:
        await session_state_service.connect()
        redis_healthy = session_state_service.redis_client is not None

        return {
            "session_id": session_id,
            "redis_healthy": redis_healthy,
            "service": "session_state",
            "status": "healthy" if redis_healthy else "degraded"
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "redis_healthy": False,
            "service": "session_state",
            "status": "unhealthy",
            "error": str(e)
        }
