"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { usePresenceWithToasts } from "../hooks/usePresenceWithToasts";
import PresenceToast from "./PresenceToast";
import NetworkStatusPill from "./NetworkStatusPill";
import CollaborativeCursors from "./CollaborativeCursors";
import UserPresenceList from "./UserPresenceList";

interface VoiceSessionWithPresenceProps {
  sessionId: string;
  role?: "operator" | "supervisor" | "observer";
  children?: React.ReactNode;
}

export default function VoiceSessionWithPresence({
  sessionId,
  role = "operator",
  children
}: VoiceSessionWithPresenceProps) {
  const { data: session } = useSession();
  const [containerRef, setContainerRef] = useState<HTMLDivElement | null>(null);

  const {
    users,
    toastEvents,
    networkStatus,
    healthStatus,
    latency,
    isConnected,
    connect,
    disconnect,
    updateCursor
  } = usePresenceWithToasts({
    sessionId,
    userId: session?.user?.id || "anonymous",
    displayName: session?.user?.name || session?.user?.email || undefined,
    role,
    onUserJoined: (user) => {
      console.log("User joined:", user);
    },
    onUserLeft: (user) => {
      console.log("User left:", user);
    }
  });

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Handle mouse movement for cursor tracking
  useEffect(() => {
    if (!containerRef || !isConnected) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = containerRef.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      // Only update if within bounds
      if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
        updateCursor(x, y);
      }
    };

    containerRef.addEventListener("mousemove", handleMouseMove);

    return () => {
      containerRef.removeEventListener("mousemove", handleMouseMove);
    };
  }, [containerRef, isConnected, updateCursor]);

  return (
    <div
      ref={setContainerRef}
      className="relative w-full h-full bg-gray-50 dark:bg-gray-900"
    >
      {/* Network Status Pill - Top Left */}
      <div className="absolute top-4 left-4 z-40">
        <NetworkStatusPill
          networkStatus={networkStatus}
          healthStatus={healthStatus}
          latency={latency}
          showDetails={true}
        />
      </div>

      {/* User Presence List - Top Right */}
      <div className="absolute top-4 right-4 z-40">
        <UserPresenceList
          users={users}
          yourUserId={session?.user?.id || "anonymous"}
        />
      </div>

      {/* Collaborative Cursors - Disabled for now, needs cursor position data */}
      {/* {containerRef && (
        <CollaborativeCursors
          cursors={new Map()}
          containerRef={containerRef}
        />
      )} */}

      {/* Presence Toasts */}
      <PresenceToast events={toastEvents} duration={3000} />

      {/* Main Content */}
      <div className="w-full h-full flex items-center justify-center">
        {children || (
          <div className="text-center">
            <div className="text-gray-600 dark:text-gray-400 mb-4">
              Voice Session: {sessionId}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-500">
              {users.length} {users.length === 1 ? "user" : "users"} in session
            </div>
          </div>
        )}
      </div>

      {/* Connection Status Overlay */}
      {!isConnected && (
        <div className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Connecting to session...
              </h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Please wait while we establish a connection to the voice session.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
