"""
Temporal workflows for mission notes with optimistic locking.

Handles concurrent updates to mission notes with conflict detection and resolution.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
import asyncio


@dataclass
class MissionNote:
    """Mission note data structure."""
    mission_id: str
    note_id: str
    content: str
    version: int
    user_id: str
    timestamp: str


@dataclass
class UpdateNoteRequest:
    """Request to update a mission note."""
    mission_id: str
    note_id: str
    content: str
    expected_version: int
    user_id: str


@dataclass
class UpdateNoteResult:
    """Result of mission note update."""
    success: bool
    current_version: int
    note: Optional[MissionNote] = None
    conflict: bool = False
    error: Optional[str] = None


@activity.defn
async def fetch_note_version(mission_id: str, note_id: str) -> int:
    """
    Fetch the current version of a mission note.

    Args:
        mission_id: Mission identifier
        note_id: Note identifier

    Returns:
        Current version number
    """
    # TODO: Implement database fetch
    # For now, simulate fetching from database
    await asyncio.sleep(0.01)  # Simulate DB latency

    # In real implementation:
    # async with get_db_session() as session:
    #     note = await session.get(MissionNote, note_id)
    #     return note.version if note else 0

    return 1  # Placeholder


@activity.defn
async def update_note_in_db(
    mission_id: str,
    note_id: str,
    content: str,
    expected_version: int,
    user_id: str
) -> UpdateNoteResult:
    """
    Update mission note in database with optimistic locking.

    Args:
        mission_id: Mission identifier
        note_id: Note identifier
        content: New note content
        expected_version: Expected version for optimistic locking
        user_id: User making the update

    Returns:
        Update result with success status and new version
    """
    # Simulate database update with optimistic locking
    await asyncio.sleep(0.01)

    # In real implementation:
    # async with get_db_session() as session:
    #     # Begin transaction
    #     async with session.begin():
    #         # Lock row for update
    #         query = select(MissionNote).where(
    #             MissionNote.mission_id == mission_id,
    #             MissionNote.note_id == note_id
    #         ).with_for_update()
    #
    #         result = await session.execute(query)
    #         note = result.scalar_one_or_none()
    #
    #         if not note:
    #             # Create new note
    #             note = MissionNote(
    #                 mission_id=mission_id,
    #                 note_id=note_id,
    #                 content=content,
    #                 version=1,
    #                 user_id=user_id,
    #                 timestamp=datetime.utcnow().isoformat()
    #             )
    #             session.add(note)
    #             await session.commit()
    #             return UpdateNoteResult(success=True, current_version=1, note=note)
    #
    #         # Check version for optimistic lock
    #         if note.version != expected_version:
    #             return UpdateNoteResult(
    #                 success=False,
    #                 current_version=note.version,
    #                 conflict=True,
    #                 error=f"Version conflict: expected {expected_version}, got {note.version}"
    #             )
    #
    #         # Update note
    #         note.content = content
    #         note.version += 1
    #         note.user_id = user_id
    #         note.timestamp = datetime.utcnow().isoformat()
    #
    #         await session.commit()
    #         return UpdateNoteResult(success=True, current_version=note.version, note=note)

    # Placeholder response
    return UpdateNoteResult(
        success=True,
        current_version=expected_version + 1,
        note=None
    )


@activity.defn
async def broadcast_note_update(mission_id: str, note_id: str, version: int):
    """
    Broadcast note update to Redis streams for real-time sync.

    Args:
        mission_id: Mission identifier
        note_id: Note identifier
        version: New version number
    """
    from app.services.redis_streams import get_redis_service

    redis_service = get_redis_service()

    await redis_service.publish_session_event(
        session_id=f"mission:{mission_id}",
        event_type="note_updated",
        data={
            "note_id": note_id,
            "version": version,
            "timestamp": "now"
        }
    )


@workflow.defn
class MissionNoteUpdateWorkflow:
    """
    Workflow for updating mission notes with optimistic locking.

    Ensures concurrent updates are handled correctly with version checking.
    """

    @workflow.run
    async def run(self, request: UpdateNoteRequest) -> UpdateNoteResult:
        """
        Execute mission note update with optimistic locking.

        Args:
            request: Update request with expected version

        Returns:
            Update result
        """
        # Configure retry policy for transient failures
        retry_policy = RetryPolicy(
            initial_interval=timedelta(milliseconds=100),
            maximum_interval=timedelta(seconds=1),
            maximum_attempts=3,
            backoff_coefficient=2.0
        )

        # Step 1: Fetch current version
        current_version = await workflow.execute_activity(
            fetch_note_version,
            args=[request.mission_id, request.note_id],
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=retry_policy
        )

        # Step 2: Check version conflict before attempting update
        if current_version != request.expected_version:
            return UpdateNoteResult(
                success=False,
                current_version=current_version,
                conflict=True,
                error=f"Version mismatch: expected {request.expected_version}, current is {current_version}"
            )

        # Step 3: Update note in database with optimistic lock
        update_result = await workflow.execute_activity(
            update_note_in_db,
            args=[
                request.mission_id,
                request.note_id,
                request.content,
                request.expected_version,
                request.user_id
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy
        )

        # Step 4: If successful, broadcast update
        if update_result.success:
            await workflow.execute_activity(
                broadcast_note_update,
                args=[request.mission_id, request.note_id, update_result.current_version],
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy
            )

        return update_result


@workflow.defn
class MissionNoteConflictResolutionWorkflow:
    """
    Workflow for resolving conflicts in mission note updates.

    Implements last-write-wins or merge strategies.
    """

    @workflow.run
    async def run(
        self,
        mission_id: str,
        note_id: str,
        conflicting_updates: list[UpdateNoteRequest]
    ) -> UpdateNoteResult:
        """
        Resolve conflicts between multiple concurrent updates.

        Args:
            mission_id: Mission identifier
            note_id: Note identifier
            conflicting_updates: List of conflicting update requests

        Returns:
            Final update result
        """
        # Sort updates by timestamp (last-write-wins strategy)
        sorted_updates = sorted(
            conflicting_updates,
            key=lambda x: x.user_id  # In real impl, use timestamp
        )

        final_update = sorted_updates[-1]

        # Fetch latest version
        current_version = await workflow.execute_activity(
            fetch_note_version,
            args=[mission_id, note_id],
            start_to_close_timeout=timedelta(seconds=5)
        )

        # Apply final update with latest version
        final_update.expected_version = current_version

        result = await workflow.execute_activity(
            update_note_in_db,
            args=[
                mission_id,
                note_id,
                final_update.content,
                current_version,
                final_update.user_id
            ],
            start_to_close_timeout=timedelta(seconds=10)
        )

        if result.success:
            await workflow.execute_activity(
                broadcast_note_update,
                args=[mission_id, note_id, result.current_version],
                start_to_close_timeout=timedelta(seconds=5)
            )

        return result
