"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useVoiceSession } from '../hooks/useVoiceSession';
import { useSessionRestoration, TranscriptChunk, QueuedAction } from '../hooks/useSessionRestoration';

interface VoiceSessionWithRestorationProps {
  sessionId?: string; // Optional: provide session ID to restore
  autoCreateSession?: boolean; // Auto-create new session if none exists
  children?: React.ReactNode;
}

export default function VoiceSessionWithRestoration({
  sessionId: initialSessionId,
  autoCreateSession = true,
  children,
}: VoiceSessionWithRestorationProps) {
  const { data: authSession } = useSession();
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(initialSessionId || null);
  const [transcripts, setTranscripts] = useState<TranscriptChunk[]>([]);
  const [restorationMessage, setRestorationMessage] = useState<string | null>(null);

  const {
    // socket, // Not returned by useVoiceSession
    agentState,
    // connectionStatus, // Not returned by useVoiceSession
    latency,
    startSession,
    stopSession,
    interrupt,
  } = useVoiceSession();

  const {
    isRestoring,
    restoredSession,
    error: restorationError,
    restoreSession,
    saveActiveSession,
    clearActiveSession,
    getSavedSession,
    queueOfflineAction,
    deviceId,
  } = useSessionRestoration({
    socket: null, // TODO: Fix socket reference
    userId: authSession?.user?.id || '',
    autoRestore: !initialSessionId, // Auto-restore only if no session ID provided
    onRestored: (data) => {
      setCurrentSessionId(data.session_id);
      setTranscripts(data.transcripts);
      setRestorationMessage(data.message);

      // Clear message after 5 seconds
      setTimeout(() => setRestorationMessage(null), 5000);
    },
    onRestoreFailed: (error) => {
      console.error('Session restoration failed:', error);
      // Auto-create new session on restore failure
      if (autoCreateSession) {
        createNewSession();
      }
    },
    onOfflineAction: (action) => {
      console.log('Replaying offline action:', action);
      // Handle offline actions (e.g., re-send transcript chunks)
      handleOfflineAction(action);
    },
  });

  // Create new session
  const createNewSession = async () => {
    if (!authSession?.user?.id) return;

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/session-state/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: authSession.user.id,
          device_id: deviceId,
          metadata: {
            created_from: 'web',
            user_agent: navigator.userAgent,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data = await response.json();
      setCurrentSessionId(data.session_id);
      saveActiveSession(data.session_id);
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  };

  // Handle offline action replay
  const handleOfflineAction = (action: QueuedAction) => {
    switch (action.type) {
      case 'transcript_chunk':
        // Re-send transcript chunk to ensure it's persisted
        // TODO: Fix socket reference
        // if (socket && socket.connected) {
        //   socket.emit('transcript_update', action.payload);
        // }
        console.log('Queued transcript chunk:', action.payload);
        break;
      case 'agent_interrupt':
        // Re-send interrupt if it wasn't processed
        interrupt();
        break;
      // Add more action types as needed
      default:
        console.warn('Unknown offline action type:', action.type);
    }
  };

  // Auto-create session on mount if needed
  useEffect(() => {
    if (!currentSessionId && autoCreateSession && authSession?.user?.id && !isRestoring) {
      const savedSession = getSavedSession();
      if (!savedSession) {
        createNewSession();
      }
    }
  }, [currentSessionId, autoCreateSession, authSession?.user?.id, isRestoring]);

  // Handle socket disconnect - queue actions
  // TODO: Fix socket reference
  // useEffect(() => {
  //   if (!socket) return;

  //   const handleDisconnect = () => {
  //     console.log('Socket disconnected - queuing mode enabled');
  //   };

  //   const handleReconnect = () => {
  //     console.log('Socket reconnected - attempting session restore');
  //     if (currentSessionId) {
  //       restoreSession(currentSessionId);
  //     }
  //   };

  //   socket.on('disconnect', handleDisconnect);
  //   socket.on('connect', handleReconnect);

  //   return () => {
  //     socket.off('disconnect', handleDisconnect);
  //     socket.off('connect', handleReconnect);
  //   };
  // }, [socket, currentSessionId, restoreSession]);

  // Listen for transcript updates
  // TODO: Fix socket reference
  useEffect(() => {
    // TODO: Fix socket reference - disabled for now
    // if (!socket) return;

    // const handleTranscript = (data: any) => {
    //   const chunk: TranscriptChunk = {
    //     id: data.id || `${Date.now()}`,
    //     speaker: data.speaker,
    //     text: data.text,
    //     timestamp: data.timestamp || new Date().toISOString(),
    //   };

    //   setTranscripts(prev => [...prev, chunk]);

    //   // If offline, queue this action
    //   if (connectionStatus !== 'connected' && currentSessionId) {
    //     queueOfflineAction(currentSessionId, 'transcript_chunk', data);
    //   }
    // };

    // socket.on('transcript', handleTranscript);

    // return () => {
    //   socket.off('transcript', handleTranscript);
    // };
  }, [currentSessionId, queueOfflineAction]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Restoration Status Banner */}
      {isRestoring && (
        <div className="bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700 px-4 py-2">
          <div className="flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent" />
            <span className="text-sm text-blue-700 dark:text-blue-300">
              Restoring your session...
            </span>
          </div>
        </div>
      )}

      {/* Restoration Success Message */}
      {restorationMessage && !isRestoring && (
        <div className="bg-green-50 dark:bg-green-900 border-b border-green-200 dark:border-green-700 px-4 py-2">
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm text-green-700 dark:text-green-300">
              {restorationMessage}
            </span>
          </div>
        </div>
      )}

      {/* Restoration Error */}
      {restorationError && !isRestoring && (
        <div className="bg-red-50 dark:bg-red-900 border-b border-red-200 dark:border-red-700 px-4 py-2">
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-4 h-4 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="text-sm text-red-700 dark:text-red-300">
              Failed to restore session: {restorationError}
            </span>
          </div>
        </div>
      )}

      {/* Session Info */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-gray-600 dark:text-gray-400">
              Session: <span className="font-mono">{currentSessionId?.substring(0, 8)}...</span>
            </span>
            <span className="text-gray-600 dark:text-gray-400">
              Device: <span className="font-mono">{deviceId?.substring(0, 12)}...</span>
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-2 h-2 rounded-full bg-gray-500" />
            <span className="text-gray-600 dark:text-gray-400 capitalize">
              Status: Ready
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {children || (
          <div className="p-8">
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Session Controls */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Voice Session Controls
                </h2>
                <div className="flex space-x-4">
                  <button
                    onClick={startSession}
                    disabled={agentState !== 'idle'}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Start Session
                  </button>
                  <button
                    onClick={stopSession}
                    disabled={agentState === 'idle'}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Stop Session
                  </button>
                  <button
                    onClick={interrupt}
                    disabled={agentState !== 'speaking'}
                    className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Interrupt
                  </button>
                </div>
                <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                  Agent State: <span className="font-semibold capitalize">{agentState}</span>
                  {latency && latency.totalRoundTrip !== undefined && (
                    <span className="ml-4">
                      Latency: <span className={`font-semibold ${latency.totalRoundTrip < 500 ? 'text-green-600' : 'text-red-600'}`}>
                        {latency.totalRoundTrip.toFixed(0)}ms
                      </span>
                    </span>
                  )}
                </div>
              </div>

              {/* Transcripts */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Transcript ({transcripts.length})
                </h2>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {transcripts.length === 0 ? (
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                      No transcripts yet. Start a session to begin.
                    </p>
                  ) : (
                    transcripts.map((chunk, index) => (
                      <div
                        key={chunk.id || index}
                        className={`p-3 rounded-lg ${
                          chunk.speaker === 'user'
                            ? 'bg-blue-50 dark:bg-blue-900'
                            : 'bg-purple-50 dark:bg-purple-900'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-1">
                          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">
                            {chunk.speaker}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {new Date(chunk.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-900 dark:text-gray-100">
                          {chunk.text}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
