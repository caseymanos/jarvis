"use client";

import { useState } from 'react';
import { DeviceInfo } from '../hooks/useMultiDeviceSync';

interface MultiDeviceIndicatorProps {
  devices: DeviceInfo[];
  deviceCount: number;
  isMultiDevice: boolean;
  currentDevice?: DeviceInfo;
  className?: string;
}

export default function MultiDeviceIndicator({
  devices,
  deviceCount,
  isMultiDevice,
  currentDevice,
  className = '',
}: MultiDeviceIndicatorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isMultiDevice) {
    return null;
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'Windows':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M0 3.45v7.11l9.53 0.04V3.45zm10.55 7.15l13.45 0.07V0l-13.45 1.92zm-10.55 1.35v7.11l9.53 1.32v-8.42zm10.55 8.47l13.45 1.9v-10.8l-13.45 0.07z" />
          </svg>
        );
      case 'macOS':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
          </svg>
        );
      case 'Linux':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12.504 0c-.155 0-.315.008-.48.021-4.226.333-3.105 4.807-3.17 6.298-.076 1.092-.3 1.953-1.05 3.02-.885 1.051-2.127 2.75-2.716 4.521-.278.832-.41 1.684-.287 2.489.845-.572 1.406-.878 2.035-.878.656 0 1.186.287 1.592.848l1.928-1.053-.239 1.176.239-.058c1.285 3.217 4.323 5.616 8.595 5.616 3.38 0 5.967-1.745 7.377-4.44l.502-1.02c.131-.26.195-.517.195-.769 0-.654-.484-1.213-1.219-1.213-.396 0-.766.164-1.102.491l-.137.154c-.315.363-.555.632-.702.787l-.275.282-.146-.146c-.317-.318-.531-.531-.695-.695l-.363-.363c-.317-.318-.695-.878-1.113-1.113l-.275-.154c-.878-.491-1.592-.878-2.127-1.113-.535-.235-1.113-.491-1.592-.491-.318 0-.654.082-.878.246l-.655.491c-.878.655-1.592 1.113-2.127 1.113-.535 0-.878-.246-1.113-.491l-.275-.275c-.317-.318-.695-.655-1.113-.878-.417-.223-.878-.491-1.592-.491z" />
          </svg>
        );
      case 'iOS':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17.5 9.5H16V6c0-2.8-2.2-5-5-5S6 3.2 6 6v3.5H4.5C3.7 9.5 3 10.2 3 11v9c0 .8.7 1.5 1.5 1.5h13c.8 0 1.5-.7 1.5-1.5v-9c0-.8-.7-1.5-1.5-1.5zM8 6c0-1.7 1.3-3 3-3s3 1.3 3 3v3.5H8V6z" />
          </svg>
        );
      case 'Android':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17.6 9.48l1.84-3.18c.16-.31.04-.69-.26-.85-.29-.15-.65-.06-.83.22l-1.88 3.24a11.5 11.5 0 0 0-8.94 0L5.65 5.67c-.19-.28-.54-.37-.83-.22-.3.16-.42.54-.26.85l1.84 3.18C2.98 10.9 1 14.55 1 18.5h22c0-3.95-1.98-7.6-5.4-9.02zM7 15.25c-.69 0-1.25-.56-1.25-1.25s.56-1.25 1.25-1.25 1.25.56 1.25 1.25-.56 1.25-1.25 1.25zm10 0c-.69 0-1.25-.56-1.25-1.25s.56-1.25 1.25-1.25 1.25.56 1.25 1.25-.56 1.25-1.25 1.25z" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z" />
          </svg>
        );
    }
  };

  const getTimeSinceActive = (lastActive: string): string => {
    const seconds = Math.floor((Date.now() - new Date(lastActive).getTime()) / 1000);
    if (seconds < 60) return 'now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className={`relative ${className}`}>
      {/* Indicator Badge */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center space-x-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        <span>{deviceCount} {deviceCount === 1 ? 'Device' : 'Devices'}</span>
        <svg
          className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Device List */}
      {isExpanded && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Connected Devices
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Session is accessible from {deviceCount} {deviceCount === 1 ? 'device' : 'devices'}
            </p>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {devices.map((device, index) => (
              <div
                key={device.device_id}
                className={`px-4 py-3 ${
                  index !== devices.length - 1 ? 'border-b border-gray-100 dark:border-gray-700' : ''
                } ${
                  device.is_current ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="text-gray-600 dark:text-gray-400 mt-0.5">
                      {getPlatformIcon(device.platform)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {device.platform}
                        </p>
                        {device.is_current && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300">
                            You
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                        {device.device_id.substring(0, 40)}...
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        <div className={`w-2 h-2 rounded-full ${
                          getTimeSinceActive(device.last_active) === 'now'
                            ? 'bg-green-500 animate-pulse'
                            : 'bg-gray-400'
                        }`} />
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Active {getTimeSinceActive(device.last_active)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 rounded-b-lg">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              All devices share the same session state, transcripts, and controls in real-time.
            </p>
          </div>
        </div>
      )}

      {/* Click Outside Overlay */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  );
}
