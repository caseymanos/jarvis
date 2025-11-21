"""
API endpoints for mission notes with optimistic locking.

Provides CRUD operations for mission notes with conflict detection.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.temporal_client import get_temporal_service
from app.workflows.mission_notes import UpdateNoteRequest, UpdateNoteResult

router = APIRouter(prefix="/missions", tags=["mission-notes"])


class CreateNoteRequest(BaseModel):
    """Request to create a mission note."""
    mission_id: str
    note_id: str
    content: str
    user_id: str


class UpdateNoteAPIRequest(BaseModel):
    """Request to update a mission note."""
    content: str
    expected_version: int
    user_id: str


class NoteResponse(BaseModel):
    """Mission note response."""
    mission_id: str
    note_id: str
    content: str
    version: int
    user_id: str
    timestamp: str


@router.post("/{mission_id}/notes")
async def create_note(mission_id: str, request: CreateNoteRequest):
    """
    Create a new mission note.

    Args:
        mission_id: Mission identifier
        request: Note creation data

    Returns:
        Created note with version 1
    """
    temporal_service = get_temporal_service()

    if not temporal_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Temporal service unavailable. Please ensure Temporal server is running."
        )

    # Create note by updating with version 0
    update_request = UpdateNoteRequest(
        mission_id=mission_id,
        note_id=request.note_id,
        content=request.content,
        expected_version=0,  # New note
        user_id=request.user_id
    )

    try:
        result = await temporal_service.execute_note_update(update_request)

        if not result.success:
            raise HTTPException(
                status_code=409,
                detail=result.error or "Failed to create note"
            )

        return {
            "success": True,
            "version": result.current_version,
            "message": "Note created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{mission_id}/notes/{note_id}")
async def update_note(
    mission_id: str,
    note_id: str,
    request: UpdateNoteAPIRequest
):
    """
    Update a mission note with optimistic locking.

    Args:
        mission_id: Mission identifier
        note_id: Note identifier
        request: Update data with expected version

    Returns:
        Updated note version or conflict error

    Raises:
        409: Version conflict - note was modified by another user
    """
    temporal_service = get_temporal_service()

    if not temporal_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Temporal service unavailable. Please ensure Temporal server is running."
        )

    update_request = UpdateNoteRequest(
        mission_id=mission_id,
        note_id=note_id,
        content=request.content,
        expected_version=request.expected_version,
        user_id=request.user_id
    )

    try:
        result = await temporal_service.execute_note_update(update_request)

        if result.conflict:
            # Version conflict - another user updated the note
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Version conflict",
                    "message": result.error,
                    "current_version": result.current_version,
                    "expected_version": request.expected_version
                }
            )

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error or "Failed to update note"
            )

        return {
            "success": True,
            "version": result.current_version,
            "message": "Note updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mission_id}/notes/{note_id}/version")
async def get_note_version(mission_id: str, note_id: str):
    """
    Get the current version of a mission note.

    Args:
        mission_id: Mission identifier
        note_id: Note identifier

    Returns:
        Current version number
    """
    # TODO: Implement direct database fetch
    # For now, return placeholder
    return {
        "mission_id": mission_id,
        "note_id": note_id,
        "version": 1
    }


@router.get("/temporal/status")
async def get_temporal_status():
    """
    Get Temporal service status.

    Returns:
        Temporal connection and worker status
    """
    temporal_service = get_temporal_service()

    return {
        "connected": temporal_service.is_connected(),
        "temporal_host": temporal_service.client.service_client.config.target_host if temporal_service.client else None,
        "namespace": "default",
        "task_queue": "jarvis-mission-notes"
    }
