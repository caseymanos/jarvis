"use client";

import { useEffect, useState, useCallback } from "react";
import { useCollaborativePresence } from "./useCollaborativePresence";
import type { PresenceEvent } from "../components/PresenceToast";
import type { NetworkStatus, HealthStatus } from "../components/NetworkStatusPill";

export interface UsePresenceWithToastsOptions {
  sessionId: string;
  userId: string;
  displayName?: string;
  role?: "operator" | "supervisor" | "observer";
  onUserJoined?: (user: any) => void;
  onUserLeft?: (user: any) => void;
}

export function usePresenceWithToasts({
  sessionId,
  userId,
  displayName,
  role = "operator",
  onUserJoined,
  onUserLeft
}: UsePresenceWithToastsOptions) {
  const [toastEvents, setToastEvents] = useState<PresenceEvent[]>([]);
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>("disconnected");
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("healthy");
  const [latency, setLatency] = useState<number | undefined>(undefined);

  const {
    users,
    connected: isConnected,
  } = useCollaborativePresence({
    sessionId,
    userId,
    displayName,
    role
  });

  // Dummy connect/disconnect/updateCursor for compatibility
  const connect = () => Promise.resolve();
  const disconnect = () => {};
  const updateCursor = (x: number, y: number) => {};

  // Track network status based on connection
  useEffect(() => {
    if (isConnected) {
      setNetworkStatus("connected");
    } else {
      setNetworkStatus("disconnected");
    }
  }, [isConnected]);

  // Listen for user joined events
  useEffect(() => {
    if (!isConnected) return;

    const handleUserJoined = (data: any) => {
      const user = data.user;

      // Create toast event
      const event: PresenceEvent = {
        id: `${user.user_id}-joined-${Date.now()}`,
        type: "joined",
        userId: user.user_id,
        callSign: user.call_sign,
        role: user.role,
        color: user.color,
        timestamp: Date.now()
      };

      setToastEvents((prev) => [...prev, event]);

      // Call custom handler
      onUserJoined?.(user);
    };

    const handleUserLeft = (data: any) => {
      // Create toast event
      const event: PresenceEvent = {
        id: `${data.user_id}-left-${Date.now()}`,
        type: "left",
        userId: data.user_id,
        callSign: data.call_sign || data.user_id,
        role: data.role || "operator",
        color: "#999999",
        timestamp: Date.now()
      };

      setToastEvents((prev) => [...prev, event]);

      // Call custom handler
      onUserLeft?.(data);
    };

    // Note: In a real implementation, you'd subscribe to Socket.IO events here
    // For now, this is a placeholder for the integration

    return () => {
      // Cleanup event listeners
    };
  }, [isConnected, onUserJoined, onUserLeft]);

  // Heartbeat for latency measurement
  useEffect(() => {
    if (!isConnected) return;

    const measureLatency = () => {
      const start = performance.now();

      // In a real implementation, you'd send a ping and measure the round-trip
      // For now, simulate latency measurement
      setTimeout(() => {
        const end = performance.now();
        const measuredLatency = Math.round(end - start);
        setLatency(measuredLatency);

        // Update health based on latency
        if (measuredLatency < 500) {
          setHealthStatus("healthy");
        } else if (measuredLatency < 1000) {
          setHealthStatus("degraded");
        } else {
          setHealthStatus("unhealthy");
        }
      }, Math.random() * 100); // Simulate network delay
    };

    measureLatency();
    const interval = setInterval(measureLatency, 5000);

    return () => clearInterval(interval);
  }, [isConnected]);

  const clearToasts = useCallback(() => {
    setToastEvents([]);
  }, []);

  return {
    users,
    toastEvents,
    networkStatus,
    healthStatus,
    latency,
    isConnected,
    connect,
    disconnect,
    updateCursor,
    clearToasts
  };
}
