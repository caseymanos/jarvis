from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import socketio
from contextlib import asynccontextmanager
import time
from datetime import datetime
from app.api import retrieval, streams, mission_notes, health as health_api, presence as presence_api, session_state
from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.services.redis_streams import get_redis_service
from app.services.temporal_client import get_temporal_service
from app.services.health_monitor import get_health_monitor
from app.services.presence import get_presence_service
from app.services.session_state import session_state_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    # Initialize database tables
    await init_db()

    redis_service = get_redis_service()
    await redis_service.connect()

    presence_service = get_presence_service()
    await presence_service.connect()

    # Connect session state service
    await session_state_service.connect()

    temporal_service = get_temporal_service()
    await temporal_service.connect()
    await temporal_service.start_worker()

    # Start health monitoring
    health_monitor = get_health_monitor()
    await health_monitor.start_monitoring(interval_seconds=5)

    yield

    # Shutdown
    await health_monitor.stop_monitoring()
    await temporal_service.disconnect()
    await session_state_service.disconnect()
    await presence_service.disconnect()
    await redis_service.disconnect()
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="Jarvis Backend API",
    description="Real-time voice assistant backend with hybrid retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Middleware to track requests and errors for health monitoring."""
    health_monitor = get_health_monitor()
    health_monitor.record_request()

    start_time = time.time()

    try:
        response = await call_next(request)

        # Record error if status code indicates failure
        if response.status_code >= 500:
            health_monitor.record_error()

        # Add latency header
        latency_ms = (time.time() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"

        return response

    except Exception as e:
        health_monitor.record_error()
        raise


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_api.router)
app.include_router(retrieval.router)
app.include_router(streams.router)
app.include_router(mission_notes.router)
app.include_router(presence_api.router)
app.include_router(session_state.router)

# Socket.IO setup (for voice streaming - to be implemented)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)
socket_app = socketio.ASGIApp(sio, app)


@app.get("/")
async def root():
    health_monitor = get_health_monitor()
    health = await health_monitor.get_current_health()

    return {
        "message": "Jarvis Backend API",
        "version": "1.0.0",
        "status": health["status"],
        "health_score": health["health_score"],
        "uptime_seconds": health["uptime_seconds"],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "retrieval": "/retrieval",
            "streams": "/streams",
            "missions": "/missions"
        }
    }


# Socket.IO events
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Client connected: {sid}")
    redis_service = get_redis_service()

    # Publish session event
    await redis_service.publish_session_event(
        session_id=sid,
        event_type="connect",
        data={"timestamp": "now"}
    )

    # Set initial agent state
    await redis_service.publish_agent_state_update(
        session_id=sid,
        state="idle"
    )


@sio.event
async def reconnect_session(sid, data):
    """
    Handle session reconnection with state restoration.

    Expected data:
        session_id: Previous session ID to restore
        user_id: User identifier
        device_id: Device identifier
    """
    from app.core.database import AsyncSessionLocal

    session_id = data.get('session_id')
    user_id = data.get('user_id')
    device_id = data.get('device_id')

    if not session_id or not user_id:
        await sio.emit('reconnect_failed', {
            'error': 'Missing session_id or user_id'
        }, room=sid)
        return

    # Get database session
    async with AsyncSessionLocal() as db:
        try:
            # Restore session state
            state = await session_state_service.get_session_state(session_id, db)

            if not state:
                await sio.emit('reconnect_failed', {
                    'error': f'Session {session_id} not found'
                }, room=sid)
                return

            # Verify user owns this session
            if state.user_id != user_id:
                await sio.emit('reconnect_failed', {
                    'error': 'Unauthorized: user does not own this session'
                }, room=sid)
                return

            # Add device to session (multi-device support)
            if device_id:
                state = await session_state_service.add_device(
                    session_id=session_id,
                    device_id=device_id,
                    db=db
                )

            # Mark session as active if it was inactive
            if not state.is_active:
                state = await session_state_service.update_state(
                    session_id=session_id,
                    metadata={'reconnected': True, 'reconnect_time': datetime.utcnow().isoformat()},
                    db=db
                )
                state.is_active = True
                await session_state_service._save_to_redis(state)

            # Replay offline queue (if any actions were queued while offline)
            queued_actions = await session_state_service.replay_offline_queue(session_id)

            # Get recent transcripts for context
            from sqlalchemy import select
            from app.models.session import TranscriptChunk
            result = await db.execute(
                select(TranscriptChunk)
                .where(TranscriptChunk.session_id == session_id)
                .where(TranscriptChunk.is_deleted == False)
                .order_by(TranscriptChunk.timestamp.desc())
                .limit(50)
            )
            transcripts = result.scalars().all()
            transcript_data = [
                {
                    'id': t.id,
                    'speaker': t.speaker,
                    'text': t.text,
                    'timestamp': t.timestamp.isoformat()
                }
                for t in reversed(transcripts)  # Oldest first
            ]

            # Send restored state to client
            await sio.emit('session_restored', {
                'session_id': session_id,
                'state': {
                    'agent_state': state.agent_state.value,
                    'is_active': state.is_active,
                    'last_activity': state.last_activity.isoformat(),
                    'transcript_count': state.transcript_count,
                    'metadata': state.metadata,
                    'device_ids': state.device_ids
                },
                'transcripts': transcript_data,
                'queued_actions': queued_actions,
                'message': f'Session restored successfully. Replayed {len(queued_actions)} offline actions.'
            }, room=sid)

            # Publish reconnection event
            redis_service = get_redis_service()
            await redis_service.publish_session_event(
                session_id=session_id,
                event_type="reconnect",
                data={
                    'user_id': user_id,
                    'device_id': device_id,
                    'offline_actions_count': len(queued_actions)
                }
            )

            print(f"Session {session_id} restored for user {user_id} with {len(queued_actions)} offline actions")

        except Exception as e:
            print(f"Error restoring session: {str(e)}")
            await sio.emit('reconnect_failed', {
                'error': f'Failed to restore session: {str(e)}'
            }, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")
    redis_service = get_redis_service()
    presence_service = get_presence_service()

    # Find user by socket and remove from presence
    user_presence = await presence_service.find_user_by_socket(sid)
    if user_presence:
        # Remove from session
        await presence_service.leave_session(user_presence.session_id, user_presence.user_id)

        # Broadcast user left via Socket.IO
        await sio.emit(
            'user_left',
            {
                'user_id': user_presence.user_id,
                'call_sign': user_presence.call_sign,
                'role': user_presence.role
            },
            room=user_presence.session_id,
            skip_sid=sid
        )

        # Publish presence event to Redis Streams
        await redis_service.publish_session_event(
            session_id=user_presence.session_id,
            event_type="user_left",
            data={
                "user_id": user_presence.user_id,
                "call_sign": user_presence.call_sign,
                "role": user_presence.role
            }
        )

    # Publish session event
    await redis_service.publish_session_event(
        session_id=sid,
        event_type="disconnect",
        data={"timestamp": "now"}
    )


@sio.event
async def audio(sid, data):
    """Handle incoming audio data."""
    print(f"Received audio from {sid}: {len(data)} bytes")
    redis_service = get_redis_service()

    # Update agent state to listening
    await redis_service.publish_agent_state_update(
        session_id=sid,
        state="listening",
        metadata={"audio_bytes": len(data)}
    )

    # TODO: Process audio, transcribe, run retrieval, generate response
    # For now, just acknowledge receipt


@sio.event
async def control(sid, data):
    """Handle control messages (start/stop/interrupt)."""
    action = data.get('action')
    print(f"Control action from {sid}: {action}")
    redis_service = get_redis_service()

    # Publish control event
    await redis_service.publish_session_event(
        session_id=sid,
        event_type=f"control_{action}",
        data=data
    )

    # Update agent state based on action
    if action == "start":
        await redis_service.publish_agent_state_update(sid, "listening")
    elif action == "stop":
        await redis_service.publish_agent_state_update(sid, "idle")
    elif action == "interrupt":
        await redis_service.publish_agent_state_update(sid, "idle")


@sio.event
async def transcript_update(sid, data):
    """Handle transcript update from client or processing pipeline."""
    redis_service = get_redis_service()

    # Broadcast transcript update to Redis stream
    await redis_service.publish_transcript_update(
        session_id=sid,
        transcript_chunk=data
    )

    # Echo back to all clients in the session (for multi-user support)
    await sio.emit('transcript', data, room=sid)


# Presence events for collaborative sessions
@sio.event
async def join_session(sid, data):
    """
    Handle user joining a collaborative session.

    Expected data:
        session_id: Session to join
        user_id: User identifier
        display_name: Optional display name
        role: User role (operator, supervisor, observer)
    """
    redis_service = get_redis_service()
    presence_service = get_presence_service()

    session_id = data.get('session_id')
    user_id = data.get('user_id')
    display_name = data.get('display_name')
    role = data.get('role', 'operator')

    # Join Socket.IO room for session
    await sio.enter_room(sid, session_id)

    # Add to presence
    presence = await presence_service.join_session(
        session_id=session_id,
        user_id=user_id,
        socket_id=sid,
        display_name=display_name,
        role=role
    )

    # Get all users in session
    all_users = await presence_service.get_session_users(session_id)

    # Send current session state to joining user
    await sio.emit('session_joined', {
        'session_id': session_id,
        'your_presence': presence_service.to_dict(presence),
        'users': [presence_service.to_dict(u) for u in all_users]
    }, room=sid)

    # Broadcast new user to other participants via Socket.IO
    await sio.emit('user_joined', {
        'user': presence_service.to_dict(presence)
    }, room=session_id, skip_sid=sid)

    # Publish presence event to Redis Streams
    await redis_service.publish_session_event(
        session_id=session_id,
        event_type="user_joined",
        data={
            "user_id": user_id,
            "call_sign": presence.call_sign,
            "role": role,
            "color": presence.color
        }
    )

    print(f"User {user_id} ({presence.call_sign}) joined session {session_id}")


@sio.event
async def leave_session(sid, data):
    """Handle user leaving a session."""
    redis_service = get_redis_service()
    presence_service = get_presence_service()

    session_id = data.get('session_id')
    user_id = data.get('user_id')

    # Get user presence before removing
    user_presence = await presence_service.get_user_presence(session_id, user_id)

    # Remove from presence
    removed = await presence_service.leave_session(session_id, user_id)

    if removed:
        # Leave Socket.IO room
        await sio.leave_room(sid, session_id)

        # Broadcast user left via Socket.IO
        await sio.emit('user_left', {
            'user_id': user_id,
            'call_sign': user_presence.call_sign if user_presence else None,
            'role': user_presence.role if user_presence else None
        }, room=session_id)

        # Publish presence event to Redis Streams
        await redis_service.publish_session_event(
            session_id=session_id,
            event_type="user_left",
            data={
                "user_id": user_id,
                "call_sign": user_presence.call_sign if user_presence else None,
                "role": user_presence.role if user_presence else None
            }
        )

        print(f"User {user_id} left session {session_id}")


@sio.event
async def cursor_move(sid, data):
    """
    Handle cursor movement for collaborative pointer.

    Expected data:
        session_id: Session identifier
        user_id: User identifier
        x: Normalized X coordinate (0.0 to 1.0)
        y: Normalized Y coordinate (0.0 to 1.0)
    """
    presence_service = get_presence_service()

    session_id = data.get('session_id')
    user_id = data.get('user_id')
    x = data.get('x', 0.0)
    y = data.get('y', 0.0)

    # Update cursor position
    presence = await presence_service.update_cursor(session_id, user_id, x, y)

    if presence:
        # Broadcast cursor position to other session participants
        await sio.emit('cursor_update', {
            'user_id': user_id,
            'call_sign': presence.call_sign,
            'color': presence.color,
            'role': presence.role,
            'x': x,
            'y': y,
            'timestamp': presence.last_active
        }, room=session_id, skip_sid=sid)


@sio.event
async def get_session_users(sid, data):
    """Get list of users in a session."""
    presence_service = get_presence_service()

    session_id = data.get('session_id')
    users = await presence_service.get_session_users(session_id)

    await sio.emit('session_users', {
        'session_id': session_id,
        'users': [presence_service.to_dict(u) for u in users]
    }, room=sid)


@sio.event
async def heartbeat(sid, data):
    """
    Handle presence heartbeat to keep user alive.

    Expected data:
        session_id: Session identifier
        user_id: User identifier
    """
    presence_service = get_presence_service()

    session_id = data.get('session_id')
    user_id = data.get('user_id')

    # Update last active timestamp
    success = await presence_service.heartbeat(session_id, user_id)

    # Acknowledge heartbeat
    if success:
        await sio.emit('heartbeat_ack', {
            'session_id': session_id,
            'user_id': user_id
        }, room=sid)


@sio.event
async def sync_event(sid, data):
    """
    Handle multi-device sync events.

    Broadcasts state changes, transcript updates, and other events
    to all devices in the same session.

    Expected data:
        session_id: Session identifier
        type: Event type (state_change, transcript_update, device_joined, device_left)
        device_id: Source device identifier
        timestamp: Event timestamp
        data: Event-specific data
    """
    session_id = data.get('session_id')
    event_type = data.get('type')
    device_id = data.get('device_id')

    if not session_id:
        return

    # Join session room if not already in it
    await sio.enter_room(sid, session_id)

    # Broadcast to all other devices in the session
    await sio.emit('sync_event', {
        'type': event_type,
        'device_id': device_id,
        'timestamp': data.get('timestamp'),
        'data': data.get('data', {}),
    }, room=session_id, skip_sid=sid)

    # Log for debugging
    print(f"Sync event {event_type} from device {device_id} in session {session_id}")


@sio.event
async def add_device_to_session(sid, data):
    """
    Add current device to a session for multi-device access.

    Expected data:
        session_id: Session to join
        user_id: User identifier
        device_id: Device identifier
    """
    from app.core.database import AsyncSessionLocal

    session_id = data.get('session_id')
    user_id = data.get('user_id')
    device_id = data.get('device_id')

    if not session_id or not device_id:
        await sio.emit('device_add_failed', {
            'error': 'Missing session_id or device_id'
        }, room=sid)
        return

    async with AsyncSessionLocal() as db:
        try:
            # Add device to session
            state = await session_state_service.add_device(
                session_id=session_id,
                device_id=device_id,
                db=db
            )

            if not state:
                await sio.emit('device_add_failed', {
                    'error': f'Session {session_id} not found'
                }, room=sid)
                return

            # Verify user owns this session
            if state.user_id != user_id:
                await sio.emit('device_add_failed', {
                    'error': 'Unauthorized: user does not own this session'
                }, room=sid)
                return

            # Join Socket.IO room for session
            await sio.enter_room(sid, session_id)

            # Notify device added successfully
            await sio.emit('device_added', {
                'session_id': session_id,
                'device_id': device_id,
                'device_count': len(state.device_ids)
            }, room=sid)

            # Broadcast to other devices in session
            await sio.emit('device_joined', {
                'device_id': device_id,
                'device_count': len(state.device_ids)
            }, room=session_id, skip_sid=sid)

            print(f"Device {device_id} added to session {session_id} ({len(state.device_ids)} total devices)")

        except Exception as e:
            print(f"Error adding device to session: {str(e)}")
            await sio.emit('device_add_failed', {
                'error': f'Failed to add device: {str(e)}'
            }, room=sid)


@sio.event
async def remove_device_from_session(sid, data):
    """
    Remove current device from a session.

    Expected data:
        session_id: Session identifier
        device_id: Device to remove
    """
    from app.core.database import AsyncSessionLocal

    session_id = data.get('session_id')
    device_id = data.get('device_id')

    if not session_id or not device_id:
        return

    async with AsyncSessionLocal() as db:
        try:
            # Remove device from session
            state = await session_state_service.remove_device(
                session_id=session_id,
                device_id=device_id,
                db=db
            )

            if state:
                # Leave Socket.IO room
                await sio.leave_room(sid, session_id)

                # Notify device removed
                await sio.emit('device_removed', {
                    'session_id': session_id,
                    'device_id': device_id,
                    'device_count': len(state.device_ids)
                }, room=sid)

                # Broadcast to other devices in session
                await sio.emit('device_left', {
                    'device_id': device_id,
                    'device_count': len(state.device_ids)
                }, room=session_id)

                print(f"Device {device_id} removed from session {session_id} ({len(state.device_ids)} remaining)")

        except Exception as e:
            print(f"Error removing device from session: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:socket_app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
