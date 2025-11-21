"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

interface UserPresence {
  user_id: string;
  session_id: string;
  call_sign: string;
  role: string;
  color: string;
  cursor_x: number;
  cursor_y: number;
  last_active: string;
  socket_id: string;
}

interface CursorPosition {
  user_id: string;
  call_sign: string;
  color: string;
  role: string;
  x: number;
  y: number;
  timestamp: string;
}

interface UseCollaborativePresenceOptions {
  sessionId: string;
  userId: string;
  displayName?: string;
  role?: 'operator' | 'supervisor' | 'observer';
  enabled?: boolean;
  throttleMs?: number; // Throttle cursor updates
}

export function useCollaborativePresence({
  sessionId,
  userId,
  displayName,
  role = 'operator',
  enabled = true,
  throttleMs = 50,
}: UseCollaborativePresenceOptions) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [cursors, setCursors] = useState<Map<string, CursorPosition>>(new Map());
  const [users, setUsers] = useState<UserPresence[]>([]);
  const [yourPresence, setYourPresence] = useState<UserPresence | null>(null);

  const lastCursorUpdate = useRef<number>(0);
  const containerRef = useRef<HTMLElement | null>(null);

  // Connect to Socket.IO
  useEffect(() => {
    if (!enabled) return;

    const socketInstance = io('http://localhost:8000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    setSocket(socketInstance);

    socketInstance.on('connect', () => {
      console.log('✓ Connected to collaborative session');
      setConnected(true);

      // Join session
      socketInstance.emit('join_session', {
        session_id: sessionId,
        user_id: userId,
        display_name: displayName,
        role: role,
      });
    });

    socketInstance.on('disconnect', () => {
      console.log('✗ Disconnected from collaborative session');
      setConnected(false);
    });

    // Handle session joined
    socketInstance.on('session_joined', (data: {
      session_id: string;
      your_presence: UserPresence;
      users: UserPresence[];
    }) => {
      console.log('✓ Joined session:', data.session_id);
      setYourPresence(data.your_presence);
      setUsers(data.users);

      // Initialize cursors for existing users
      const newCursors = new Map<string, CursorPosition>();
      data.users.forEach(user => {
        if (user.user_id !== userId) {
          newCursors.set(user.user_id, {
            user_id: user.user_id,
            call_sign: user.call_sign,
            color: user.color,
            role: user.role,
            x: user.cursor_x,
            y: user.cursor_y,
            timestamp: user.last_active,
          });
        }
      });
      setCursors(newCursors);
    });

    // Handle new user joining
    socketInstance.on('user_joined', (data: { user: UserPresence }) => {
      console.log('User joined:', data.user.call_sign);
      setUsers(prev => [...prev, data.user]);
    });

    // Handle user leaving
    socketInstance.on('user_left', (data: { user_id: string }) => {
      console.log('User left:', data.user_id);
      setUsers(prev => prev.filter(u => u.user_id !== data.user_id));
      setCursors(prev => {
        const newCursors = new Map(prev);
        newCursors.delete(data.user_id);
        return newCursors;
      });
    });

    // Handle cursor updates
    socketInstance.on('cursor_update', (data: CursorPosition) => {
      setCursors(prev => {
        const newCursors = new Map(prev);
        newCursors.set(data.user_id, data);
        return newCursors;
      });
    });

    return () => {
      socketInstance.emit('leave_session', {
        session_id: sessionId,
        user_id: userId,
      });
      socketInstance.disconnect();
    };
  }, [enabled, sessionId, userId, displayName, role]);

  // Send cursor position
  const sendCursorPosition = useCallback((x: number, y: number) => {
    if (!socket || !connected) return;

    const now = Date.now();
    if (now - lastCursorUpdate.current < throttleMs) {
      return; // Throttle updates
    }

    lastCursorUpdate.current = now;

    socket.emit('cursor_move', {
      session_id: sessionId,
      user_id: userId,
      x: x,
      y: y,
    });
  }, [socket, connected, sessionId, userId, throttleMs]);

  // Track mouse movement
  useEffect(() => {
    if (!enabled || !connected) return;

    const handleMouseMove = (event: MouseEvent) => {
      const container = containerRef.current || document.body;
      const rect = container.getBoundingClientRect();

      // Normalize coordinates to 0-1
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;

      // Clamp to valid range
      const clampedX = Math.max(0, Math.min(1, x));
      const clampedY = Math.max(0, Math.min(1, y));

      sendCursorPosition(clampedX, clampedY);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [enabled, connected, sendCursorPosition]);

  return {
    connected,
    cursors,
    users,
    yourPresence,
    containerRef,
  };
}
