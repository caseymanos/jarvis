"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import { Socket } from 'socket.io-client';

export interface SessionState {
  agent_state: 'idle' | 'listening' | 'thinking' | 'speaking';
  is_active: boolean;
  last_activity: string;
  transcript_count: number;
  metadata: Record<string, any>;
  device_ids: string[];
}

export interface TranscriptChunk {
  id: string;
  speaker: 'user' | 'agent';
  text: string;
  timestamp: string;
}

export interface QueuedAction {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
  queued_at: string;
}

export interface RestoredSession {
  session_id: string;
  state: SessionState;
  transcripts: TranscriptChunk[];
  queued_actions: QueuedAction[];
  message: string;
}

interface UseSessionRestorationOptions {
  socket: Socket | null;
  userId: string;
  deviceId?: string;
  autoRestore?: boolean; // Auto-restore on mount if session in localStorage
  onRestored?: (data: RestoredSession) => void;
  onRestoreFailed?: (error: string) => void;
  onOfflineAction?: (action: QueuedAction) => void;
}

const SESSION_STORAGE_KEY = 'jarvis_active_session';

/**
 * Hook for handling session reconnection and state restoration
 *
 * Features:
 * - Automatic session restoration on page refresh
 * - Offline action queuing and replay
 * - Multi-device session continuity
 * - Transcript history restoration
 */
export function useSessionRestoration({
  socket,
  userId,
  deviceId,
  autoRestore = true,
  onRestored,
  onRestoreFailed,
  onOfflineAction,
}: UseSessionRestorationOptions) {
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoredSession, setRestoredSession] = useState<RestoredSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasAttemptedRestore = useRef(false);

  // Get device ID (use provided or generate from browser fingerprint)
  const getDeviceId = useCallback(() => {
    if (deviceId) return deviceId;

    // Simple device fingerprint (can be enhanced)
    const stored = localStorage.getItem('jarvis_device_id');
    if (stored) return stored;

    const newDeviceId = `${navigator.userAgent}-${screen.width}x${screen.height}-${Date.now()}`.substring(0, 50);
    localStorage.setItem('jarvis_device_id', newDeviceId);
    return newDeviceId;
  }, [deviceId]);

  // Save active session to localStorage
  const saveActiveSession = useCallback((sessionId: string) => {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({
      session_id: sessionId,
      user_id: userId,
      saved_at: new Date().toISOString(),
    }));
  }, [userId]);

  // Clear active session from localStorage
  const clearActiveSession = useCallback(() => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }, []);

  // Get saved session from localStorage
  const getSavedSession = useCallback(() => {
    try {
      const stored = localStorage.getItem(SESSION_STORAGE_KEY);
      if (!stored) return null;

      const data = JSON.parse(stored);

      // Check if session is too old (> 24 hours)
      const savedAt = new Date(data.saved_at);
      const hoursSince = (Date.now() - savedAt.getTime()) / (1000 * 60 * 60);
      if (hoursSince > 24) {
        clearActiveSession();
        return null;
      }

      // Verify user matches
      if (data.user_id !== userId) {
        clearActiveSession();
        return null;
      }

      return data.session_id;
    } catch (e) {
      clearActiveSession();
      return null;
    }
  }, [userId, clearActiveSession]);

  // Restore a session
  const restoreSession = useCallback(async (sessionId: string) => {
    if (!socket || !socket.connected) {
      setError('Socket not connected');
      onRestoreFailed?.('Socket not connected');
      return;
    }

    setIsRestoring(true);
    setError(null);

    socket.emit('reconnect_session', {
      session_id: sessionId,
      user_id: userId,
      device_id: getDeviceId(),
    });
  }, [socket, userId, getDeviceId, onRestoreFailed]);

  // Auto-restore on mount
  useEffect(() => {
    if (!autoRestore || hasAttemptedRestore.current) return;
    if (!socket || !socket.connected) return;

    const savedSessionId = getSavedSession();
    if (savedSessionId) {
      hasAttemptedRestore.current = true;
      restoreSession(savedSessionId);
    }
  }, [autoRestore, socket, getSavedSession, restoreSession]);

  // Listen for restoration events
  useEffect(() => {
    if (!socket) return;

    const handleSessionRestored = (data: RestoredSession) => {
      console.log('Session restored:', data);
      setIsRestoring(false);
      setRestoredSession(data);
      setError(null);

      // Save to localStorage
      saveActiveSession(data.session_id);

      // Process offline actions
      if (data.queued_actions && data.queued_actions.length > 0) {
        data.queued_actions.forEach(action => {
          onOfflineAction?.(action);
        });
      }

      onRestored?.(data);
    };

    const handleReconnectFailed = (data: { error: string }) => {
      console.error('Reconnect failed:', data.error);
      setIsRestoring(false);
      setError(data.error);
      clearActiveSession();
      onRestoreFailed?.(data.error);
    };

    socket.on('session_restored', handleSessionRestored);
    socket.on('reconnect_failed', handleReconnectFailed);

    return () => {
      socket.off('session_restored', handleSessionRestored);
      socket.off('reconnect_failed', handleReconnectFailed);
    };
  }, [socket, saveActiveSession, clearActiveSession, onRestored, onRestoreFailed, onOfflineAction]);

  // Queue offline action (when socket disconnected)
  const queueOfflineAction = useCallback(async (
    sessionId: string,
    actionType: string,
    payload: Record<string, any>
  ) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/session-state/${sessionId}/queue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action_type: actionType,
          payload,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to queue action');
      }

      return true;
    } catch (e) {
      console.error('Failed to queue offline action:', e);
      return false;
    }
  }, []);

  return {
    isRestoring,
    restoredSession,
    error,
    restoreSession,
    saveActiveSession,
    clearActiveSession,
    getSavedSession,
    queueOfflineAction,
    deviceId: getDeviceId(),
  };
}
