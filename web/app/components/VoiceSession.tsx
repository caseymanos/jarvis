"use client";

import { useVoiceSession } from '../hooks/useVoiceSession';
import { useEffect, useRef } from 'react';

export default function VoiceSession() {
  const {
    isActive,
    agentState,
    transcript,
    response,
    error,
    volumeLevel,
    latency,
    isConnected,
    startSession,
    stopSession,
    interrupt,
    getWaveformData,
  } = useVoiceSession();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>(0);

  useEffect(() => {
    if (!isActive || !canvasRef.current) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const waveformData = getWaveformData();
      const width = canvas.width;
      const height = canvas.height;

      ctx.fillStyle = 'rgb(17, 24, 39)';
      ctx.fillRect(0, 0, width, height);

      ctx.lineWidth = 2;
      ctx.strokeStyle = agentState === 'listening' ? 'rgb(59, 130, 246)' :
                        agentState === 'thinking' ? 'rgb(251, 191, 36)' :
                        agentState === 'speaking' ? 'rgb(34, 197, 94)' : 'rgb(107, 114, 128)';

      ctx.beginPath();

      const sliceWidth = width / waveformData.length;
      let x = 0;

      for (let i = 0; i < waveformData.length; i++) {
        const v = waveformData[i] / 128.0;
        const y = (v * height) / 2;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }

        x += sliceWidth;
      }

      ctx.lineTo(width, height / 2);
      ctx.stroke();

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, agentState, getWaveformData]);

  const getStateColor = () => {
    switch (agentState) {
      case 'listening':
        return 'text-blue-500';
      case 'thinking':
        return 'text-yellow-500';
      case 'speaking':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStateText = () => {
    switch (agentState) {
      case 'listening':
        return 'Listening...';
      case 'thinking':
        return 'Processing...';
      case 'speaking':
        return 'Responding...';
      default:
        return 'Idle';
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            <span className={`font-semibold ${getStateColor()}`}>
              {getStateText()}
            </span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Latency: {latency.totalRoundTrip.toFixed(0)}ms
          </div>
        </div>

        <canvas
          ref={canvasRef}
          width={800}
          height={200}
          className="w-full bg-gray-900 rounded-lg mb-4"
        />

        <div className="flex items-center space-x-4">
          <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
            <div className="flex items-center space-x-2">
              <div className="text-sm text-gray-500 dark:text-gray-400">Volume:</div>
              <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-100"
                  style={{ width: `${volumeLevel * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex space-x-3">
          {!isActive ? (
            <button
              onClick={startSession}
              className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Start Voice Session
            </button>
          ) : (
            <>
              <button
                onClick={interrupt}
                disabled={agentState !== 'speaking'}
                className="flex-1 px-6 py-3 bg-yellow-600 hover:bg-yellow-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Interrupt
              </button>
              <button
                onClick={stopSession}
                className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Stop Session
              </button>
            </>
          )}
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}
      </div>

      {(transcript || response) && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4">
          {transcript && (
            <div>
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">
                Your Question:
              </h3>
              <p className="text-gray-900 dark:text-white">{transcript}</p>
            </div>
          )}

          {response && (
            <div>
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">
                Response:
              </h3>
              <p className="text-gray-900 dark:text-white">{response}</p>
            </div>
          )}
        </div>
      )}

      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Latency Metrics
        </h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500 dark:text-gray-400">Capture → Server</div>
            <div className="font-mono text-gray-900 dark:text-white">
              {latency.captureToServer.toFixed(0)}ms
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Server Processing</div>
            <div className="font-mono text-gray-900 dark:text-white">
              {latency.serverProcessing.toFixed(0)}ms
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Total Round-Trip</div>
            <div className={`font-mono font-semibold ${
              latency.totalRoundTrip < 500 ? 'text-green-600' : 'text-red-600'
            }`}>
              {latency.totalRoundTrip.toFixed(0)}ms
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
