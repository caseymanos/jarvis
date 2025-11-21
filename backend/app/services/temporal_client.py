"""
Temporal client service for workflow execution.

Manages Temporal client connection and workflow execution.
"""

from typing import Optional
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker
from app.core.config import get_settings
from app.workflows.mission_notes import (
    MissionNoteUpdateWorkflow,
    MissionNoteConflictResolutionWorkflow,
    UpdateNoteRequest,
    UpdateNoteResult,
    fetch_note_version,
    update_note_in_db,
    broadcast_note_update
)

settings = get_settings()


class TemporalService:
    """Service for managing Temporal workflows."""

    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None

    async def connect(self):
        """Connect to Temporal server."""
        try:
            self.client = await Client.connect(
                settings.temporal_host,
                namespace=settings.temporal_namespace
            )
            print(f"✓ Connected to Temporal at {settings.temporal_host}")
        except Exception as e:
            print(f"✗ Failed to connect to Temporal: {e}")
            print(f"  Note: Temporal server must be running at {settings.temporal_host}")
            print(f"  Install: https://docs.temporal.io/cli#install")
            # Don't raise - allow app to start without Temporal for development
            self.client = None

    async def start_worker(self):
        """Start Temporal worker for processing workflows."""
        if not self.client:
            print("✗ Cannot start worker: Temporal client not connected")
            return

        try:
            self.worker = Worker(
                self.client,
                task_queue=settings.temporal_task_queue,
                workflows=[
                    MissionNoteUpdateWorkflow,
                    MissionNoteConflictResolutionWorkflow
                ],
                activities=[
                    fetch_note_version,
                    update_note_in_db,
                    broadcast_note_update
                ]
            )

            # Run worker in background
            import asyncio
            asyncio.create_task(self.worker.run())
            print(f"✓ Temporal worker started on queue '{settings.temporal_task_queue}'")

        except Exception as e:
            print(f"✗ Failed to start Temporal worker: {e}")
            self.worker = None

    async def disconnect(self):
        """Disconnect from Temporal."""
        if self.worker:
            await self.worker.shutdown()
            print("✓ Temporal worker stopped")

        if self.client:
            # Temporal client doesn't need explicit close
            print("✓ Disconnected from Temporal")

    async def execute_note_update(
        self,
        request: UpdateNoteRequest,
        workflow_id: Optional[str] = None
    ) -> UpdateNoteResult:
        """
        Execute mission note update workflow.

        Args:
            request: Update request
            workflow_id: Optional workflow ID (defaults to note_id)

        Returns:
            Update result

        Raises:
            RuntimeError: If Temporal client not connected
        """
        if not self.client:
            raise RuntimeError("Temporal client not connected")

        if workflow_id is None:
            workflow_id = f"note-update-{request.mission_id}-{request.note_id}"

        # Start workflow
        handle = await self.client.start_workflow(
            MissionNoteUpdateWorkflow.run,
            request,
            id=workflow_id,
            task_queue=settings.temporal_task_queue
        )

        # Wait for result
        result = await handle.result()
        return result

    async def execute_conflict_resolution(
        self,
        mission_id: str,
        note_id: str,
        conflicting_updates: list[UpdateNoteRequest]
    ) -> UpdateNoteResult:
        """
        Execute conflict resolution workflow.

        Args:
            mission_id: Mission identifier
            note_id: Note identifier
            conflicting_updates: List of conflicting updates

        Returns:
            Resolution result

        Raises:
            RuntimeError: If Temporal client not connected
        """
        if not self.client:
            raise RuntimeError("Temporal client not connected")

        workflow_id = f"conflict-resolution-{mission_id}-{note_id}"

        handle = await self.client.start_workflow(
            MissionNoteConflictResolutionWorkflow.run,
            args=[mission_id, note_id, conflicting_updates],
            id=workflow_id,
            task_queue=settings.temporal_task_queue
        )

        result = await handle.result()
        return result

    async def get_workflow_handle(self, workflow_id: str) -> Optional[WorkflowHandle]:
        """
        Get handle to running workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow handle or None if not found
        """
        if not self.client:
            return None

        try:
            handle = self.client.get_workflow_handle(workflow_id)
            return handle
        except Exception:
            return None

    def is_connected(self) -> bool:
        """Check if Temporal client is connected."""
        return self.client is not None


# Singleton instance
_temporal_service: Optional[TemporalService] = None


def get_temporal_service() -> TemporalService:
    """Get or create Temporal service singleton."""
    global _temporal_service
    if _temporal_service is None:
        _temporal_service = TemporalService()
    return _temporal_service
