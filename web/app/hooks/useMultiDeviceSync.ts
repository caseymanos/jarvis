"use client";

import { useEffect, useState, useCallback } from 'react';
import { Socket } from 'socket.io-client';

export interface DeviceInfo {
  device_id: string;
  user_agent: string;
  platform: string;
  last_active: string;
  is_current: boolean;
}

export interface SyncEvent {
  type: 'state_change' | 'transcript_update' | 'device_joined' | 'device_left';
  device_id: string;
  timestamp: string;
  data: any;
}

interface UseMultiDeviceSyncOptions {
  socket: Socket | null;
  sessionId: string | null;
  deviceId: string;
  onDeviceJoined?: (deviceInfo: DeviceInfo) => void;
  onDeviceLeft?: (deviceId: string) => void;
  onSyncEvent?: (event: SyncEvent) => void;
}

/**
 * Hook for managing multi-device session synchronization
 *
 * Features:
 * - Track all devices connected to a session
 * - Sync state changes across devices
 * - Notify when devices join/leave
 * - Prevent duplicate actions across devices
 */
export function useMultiDeviceSync({
  socket,
  sessionId,
  deviceId,
  onDeviceJoined,
  onDeviceLeft,
  onSyncEvent,
}: UseMultiDeviceSyncOptions) {
  const [connectedDevices, setConnectedDevices] = useState<DeviceInfo[]>([]);
  const [isMultiDevice, setIsMultiDevice] = useState(false);

  // Fetch connected devices
  const fetchDevices = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/session-state/${sessionId}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch session state');
      }

      const data = await response.json();
      const deviceIds = data.device_ids || [];

      // Create device info for each connected device
      const devices: DeviceInfo[] = deviceIds.map((id: string) => ({
        device_id: id,
        user_agent: id.includes('Mozilla') ? 'Browser' : 'Mobile',
        platform: getPlatformFromDeviceId(id),
        last_active: new Date().toISOString(),
        is_current: id === deviceId,
      }));

      setConnectedDevices(devices);
      setIsMultiDevice(deviceIds.length > 1);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  }, [sessionId, deviceId]);

  // Get platform from device ID (simple heuristic)
  const getPlatformFromDeviceId = (id: string): string => {
    if (id.includes('Windows')) return 'Windows';
    if (id.includes('Mac')) return 'macOS';
    if (id.includes('Linux')) return 'Linux';
    if (id.includes('iPhone') || id.includes('iPad')) return 'iOS';
    if (id.includes('Android')) return 'Android';
    return 'Unknown';
  };

  // Broadcast sync event to other devices
  const broadcastSyncEvent = useCallback((
    type: SyncEvent['type'],
    data: any
  ) => {
    if (!socket || !sessionId) return;

    const event: SyncEvent = {
      type,
      device_id: deviceId,
      timestamp: new Date().toISOString(),
      data,
    };

    socket.emit('sync_event', {
      session_id: sessionId,
      ...event,
    });
  }, [socket, sessionId, deviceId]);

  // Handle device added to session
  const handleDeviceAdded = useCallback((data: { device_id: string }) => {
    const newDevice: DeviceInfo = {
      device_id: data.device_id,
      user_agent: 'Unknown',
      platform: getPlatformFromDeviceId(data.device_id),
      last_active: new Date().toISOString(),
      is_current: data.device_id === deviceId,
    };

    setConnectedDevices(prev => {
      // Avoid duplicates
      if (prev.some(d => d.device_id === data.device_id)) {
        return prev;
      }
      return [...prev, newDevice];
    });

    setIsMultiDevice(true);
    onDeviceJoined?.(newDevice);
  }, [deviceId, onDeviceJoined]);

  // Handle device removed from session
  const handleDeviceRemoved = useCallback((data: { device_id: string }) => {
    setConnectedDevices(prev => {
      const updated = prev.filter(d => d.device_id !== data.device_id);
      setIsMultiDevice(updated.length > 1);
      return updated;
    });

    onDeviceLeft?.(data.device_id);
  }, [onDeviceLeft]);

  // Handle sync event from another device
  const handleSyncEvent = useCallback((event: SyncEvent) => {
    // Ignore events from current device
    if (event.device_id === deviceId) return;

    console.log('Received sync event from another device:', event);
    onSyncEvent?.(event);

    // Update last active for the device
    setConnectedDevices(prev =>
      prev.map(d =>
        d.device_id === event.device_id
          ? { ...d, last_active: event.timestamp }
          : d
      )
    );
  }, [deviceId, onSyncEvent]);

  // Fetch devices on mount and when session changes
  useEffect(() => {
    if (sessionId) {
      fetchDevices();
    }
  }, [sessionId, fetchDevices]);

  // Listen for device join/leave events
  useEffect(() => {
    if (!socket) return;

    socket.on('device_joined', handleDeviceAdded);
    socket.on('device_left', handleDeviceRemoved);
    socket.on('sync_event', handleSyncEvent);

    return () => {
      socket.off('device_joined', handleDeviceAdded);
      socket.off('device_left', handleDeviceRemoved);
      socket.off('sync_event', handleSyncEvent);
    };
  }, [socket, handleDeviceAdded, handleDeviceRemoved, handleSyncEvent]);

  // Periodic refresh of device list (every 30 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchDevices]);

  return {
    connectedDevices,
    isMultiDevice,
    deviceCount: connectedDevices.length,
    currentDevice: connectedDevices.find(d => d.is_current),
    otherDevices: connectedDevices.filter(d => !d.is_current),
    broadcastSyncEvent,
    refreshDevices: fetchDevices,
  };
}
