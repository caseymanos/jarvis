"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { AudioProcessor } from '../lib/audio-processor';
import { VoiceWebSocketClient, ResponseMessage, LatencyMetrics } from '../lib/websocket-client';

export type AgentState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceSessionState {
  isActive: boolean;
  agentState: AgentState;
  transcript: string;
  response: string | null;
  error: string | null;
  volumeLevel: number;
  latency: LatencyMetrics;
  isConnected: boolean;
}

interface UseVoiceSessionReturn extends VoiceSessionState {
  startSession: () => Promise<void>;
  stopSession: () => void;
  interrupt: () => void;
  getWaveformData: () => Uint8Array;
}

export function useVoiceSession(
  websocketUrl: string = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'http://localhost:8000'
): UseVoiceSessionReturn {
  const [state, setState] = useState<VoiceSessionState>({
    isActive: false,
    agentState: 'idle',
    transcript: '',
    response: null,
    error: null,
    volumeLevel: 0,
    latency: {
      captureToServer: 0,
      serverProcessing: 0,
      totalRoundTrip: 0,
    },
    isConnected: false,
  });

  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const wsClientRef = useRef<VoiceWebSocketClient | null>(null);
  const volumeIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (audioProcessorRef.current) {
        audioProcessorRef.current.stop();
      }
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
      if (volumeIntervalRef.current) {
        clearInterval(volumeIntervalRef.current);
      }
    };
  }, []);

  const startSession = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, error: null }));

      wsClientRef.current = new VoiceWebSocketClient();
      await wsClientRef.current.connect(websocketUrl);

      setState((prev) => ({ ...prev, isConnected: true }));

      wsClientRef.current.onResponse((message: ResponseMessage) => {
        setState((prev) => ({
          ...prev,
          response: message.text,
          agentState: 'idle',
          latency: wsClientRef.current?.getLatencyMetrics() || prev.latency,
        }));
      });

      wsClientRef.current.onTranscript((text: string) => {
        setState((prev) => ({
          ...prev,
          transcript: text,
        }));
      });

      wsClientRef.current.onError((error: string) => {
        setState((prev) => ({
          ...prev,
          error,
          agentState: 'idle',
        }));
      });

      wsClientRef.current.onAgentState((agentState: AgentState) => {
        setState((prev) => ({
          ...prev,
          agentState,
        }));
      });

      audioProcessorRef.current = new AudioProcessor();
      await audioProcessorRef.current.initialize((audioData: Float32Array) => {
        if (wsClientRef.current && wsClientRef.current.isConnected()) {
          wsClientRef.current.sendAudio(audioData);
        }
      });

      wsClientRef.current.sendControl('start');

      volumeIntervalRef.current = setInterval(() => {
        if (audioProcessorRef.current) {
          const volumeLevel = audioProcessorRef.current.getVolumeLevel();
          setState((prev) => ({ ...prev, volumeLevel }));
        }
      }, 100);

      setState((prev) => ({
        ...prev,
        isActive: true,
        agentState: 'listening',
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start session';
      setState((prev) => ({
        ...prev,
        error: errorMessage,
        isActive: false,
      }));
      throw error;
    }
  }, [websocketUrl]);

  const stopSession = useCallback(() => {
    if (wsClientRef.current) {
      wsClientRef.current.sendControl('stop');
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }

    if (audioProcessorRef.current) {
      audioProcessorRef.current.stop();
      audioProcessorRef.current = null;
    }

    if (volumeIntervalRef.current) {
      clearInterval(volumeIntervalRef.current);
      volumeIntervalRef.current = null;
    }

    setState({
      isActive: false,
      agentState: 'idle',
      transcript: '',
      response: null,
      error: null,
      volumeLevel: 0,
      latency: {
        captureToServer: 0,
        serverProcessing: 0,
        totalRoundTrip: 0,
      },
      isConnected: false,
    });
  }, []);

  const interrupt = useCallback(() => {
    if (wsClientRef.current && wsClientRef.current.isConnected()) {
      wsClientRef.current.sendControl('interrupt');
      setState((prev) => ({
        ...prev,
        agentState: 'listening',
        response: null,
      }));
    }
  }, []);

  const getWaveformData = useCallback((): Uint8Array => {
    if (audioProcessorRef.current) {
      return audioProcessorRef.current.getWaveformData();
    }
    return new Uint8Array(0);
  }, []);

  return {
    ...state,
    startSession,
    stopSession,
    interrupt,
    getWaveformData,
  };
}
