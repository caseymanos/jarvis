import { io, Socket } from 'socket.io-client';

export type MessageType = 'audio' | 'control' | 'response' | 'error' | 'latency';

export interface AudioMessage {
  type: 'audio';
  data: Float32Array;
  timestamp: number;
}

export interface ControlMessage {
  type: 'control';
  action: 'start' | 'stop' | 'interrupt';
  timestamp: number;
}

export interface ResponseMessage {
  type: 'response';
  text: string;
  audioUrl?: string;
  sources?: string[];
  confidence?: number;
  timestamp: number;
}

export interface LatencyMetrics {
  captureToServer: number;
  serverProcessing: number;
  totalRoundTrip: number;
}

export class VoiceWebSocketClient {
  private socket: Socket | null = null;
  private latencyStart: number = 0;
  private latencyMetrics: LatencyMetrics = {
    captureToServer: 0,
    serverProcessing: 0,
    totalRoundTrip: 0,
  };

  connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
      });
    });
  }

  sendAudio(audioData: Float32Array): void {
    if (!this.socket || !this.socket.connected) {
      console.warn('Socket not connected');
      return;
    }

    this.latencyStart = performance.now();

    const buffer = audioData.buffer.slice(
      audioData.byteOffset,
      audioData.byteOffset + audioData.byteLength
    );

    this.socket.emit('audio', {
      data: buffer,
      timestamp: Date.now(),
    });
  }

  sendControl(action: 'start' | 'stop' | 'interrupt'): void {
    if (!this.socket || !this.socket.connected) {
      console.warn('Socket not connected');
      return;
    }

    this.socket.emit('control', {
      action,
      timestamp: Date.now(),
    });
  }

  onResponse(callback: (message: ResponseMessage) => void): void {
    if (!this.socket) return;

    this.socket.on('response', (data) => {
      const latency = performance.now() - this.latencyStart;
      this.latencyMetrics.totalRoundTrip = latency;

      callback({
        type: 'response',
        text: data.text,
        audioUrl: data.audioUrl,
        sources: data.sources,
        confidence: data.confidence,
        timestamp: data.timestamp,
      });
    });
  }

  onTranscript(callback: (text: string) => void): void {
    if (!this.socket) return;

    this.socket.on('transcript', (data) => {
      callback(data.text);
    });
  }

  onError(callback: (error: string) => void): void {
    if (!this.socket) return;

    this.socket.on('error', (data) => {
      callback(data.message || 'Unknown error');
    });
  }

  onAgentState(callback: (state: 'idle' | 'listening' | 'thinking' | 'speaking') => void): void {
    if (!this.socket) return;

    this.socket.on('agent_state', (data) => {
      callback(data.state);
    });
  }

  getLatencyMetrics(): LatencyMetrics {
    return { ...this.latencyMetrics };
  }

  isConnected(): boolean {
    return this.socket !== null && this.socket.connected;
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}
