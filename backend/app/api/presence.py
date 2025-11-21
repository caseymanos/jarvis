"""
API endpoints for collaborative presence.

Provides HTTP endpoints for presence queries and management.
"""

from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from app.services.presence import get_presence_service

router = APIRouter(prefix="/presence", tags=["presence"])


class PresenceInfo(BaseModel):
    """Presence information response."""
    user_id: str
    session_id: str
    call_sign: str
    role: str
    color: str
    cursor_x: float
    cursor_y: float
    last_active: str


@router.get("/session/{session_id}/users")
async def get_session_users(session_id: str) -> List[PresenceInfo]:
    """
    Get list of users currently in a session.

    Args:
        session_id: Session identifier

    Returns:
        List of user presences
    """
    presence_service = get_presence_service()
    users = presence_service.get_session_users(session_id)

    return [
        PresenceInfo(
            user_id=u.user_id,
            session_id=u.session_id,
            call_sign=u.call_sign,
            role=u.role,
            color=u.color,
            cursor_x=u.cursor_x,
            cursor_y=u.cursor_y,
            last_active=u.last_active
        )
        for u in users
    ]


@router.get("/session/{session_id}/user/{user_id}")
async def get_user_presence(session_id: str, user_id: str):
    """
    Get specific user's presence in a session.

    Args:
        session_id: Session identifier
        user_id: User identifier

    Returns:
        User presence or 404
    """
    presence_service = get_presence_service()
    presence = presence_service.get_user_presence(session_id, user_id)

    if not presence:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found in session")

    return PresenceInfo(
        user_id=presence.user_id,
        session_id=presence.session_id,
        call_sign=presence.call_sign,
        role=presence.role,
        color=presence.color,
        cursor_x=presence.cursor_x,
        cursor_y=presence.cursor_y,
        last_active=presence.last_active
    )


@router.get("/sessions")
async def list_active_sessions():
    """
    Get list of active sessions with user counts.

    Returns:
        List of active sessions
    """
    presence_service = get_presence_service()

    sessions = []
    for session_id, users in presence_service.sessions.items():
        sessions.append({
            "session_id": session_id,
            "user_count": len(users),
            "users": [u.call_sign for u in users.values()]
        })

    return {"sessions": sessions}


@router.get("/colors")
async def get_available_colors():
    """
    Get the color palette used for cursor assignment.

    Returns:
        List of available colors
    """
    from app.services.presence import PresenceService

    return {
        "colors": PresenceService.CURSOR_COLORS,
        "total": len(PresenceService.CURSOR_COLORS)
    }
