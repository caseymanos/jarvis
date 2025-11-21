"use client";

import { motion } from "framer-motion";

export type NetworkStatus = "connected" | "connecting" | "disconnected" | "error";
export type HealthStatus = "healthy" | "degraded" | "unhealthy";

interface NetworkStatusPillProps {
  networkStatus: NetworkStatus;
  healthStatus?: HealthStatus;
  latency?: number;
  showDetails?: boolean;
}

export default function NetworkStatusPill({
  networkStatus,
  healthStatus = "healthy",
  latency,
  showDetails = true
}: NetworkStatusPillProps) {
  const getNetworkConfig = () => {
    switch (networkStatus) {
      case "connected":
        return {
          color: "bg-green-500",
          textColor: "text-green-700 dark:text-green-300",
          bgColor: "bg-green-50 dark:bg-green-900/20",
          borderColor: "border-green-200 dark:border-green-800",
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          ),
          label: "Connected"
        };
      case "connecting":
        return {
          color: "bg-yellow-500",
          textColor: "text-yellow-700 dark:text-yellow-300",
          bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
          borderColor: "border-yellow-200 dark:border-yellow-800",
          icon: (
            <motion.svg
              className="w-4 h-4"
              fill="currentColor"
              viewBox="0 0 20 20"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <path
                fillRule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clipRule="evenodd"
              />
            </motion.svg>
          ),
          label: "Connecting"
        };
      case "disconnected":
        return {
          color: "bg-gray-500",
          textColor: "text-gray-700 dark:text-gray-300",
          bgColor: "bg-gray-50 dark:bg-gray-900/20",
          borderColor: "border-gray-200 dark:border-gray-800",
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          ),
          label: "Disconnected"
        };
      case "error":
        return {
          color: "bg-red-500",
          textColor: "text-red-700 dark:text-red-300",
          bgColor: "bg-red-50 dark:bg-red-900/20",
          borderColor: "border-red-200 dark:border-red-800",
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          ),
          label: "Error"
        };
    }
  };

  const getHealthConfig = () => {
    switch (healthStatus) {
      case "healthy":
        return { color: "text-green-600 dark:text-green-400", label: "Healthy" };
      case "degraded":
        return { color: "text-yellow-600 dark:text-yellow-400", label: "Degraded" };
      case "unhealthy":
        return { color: "text-red-600 dark:text-red-400", label: "Unhealthy" };
    }
  };

  const getLatencyColor = () => {
    if (!latency) return "";
    if (latency < 500) return "text-green-600 dark:text-green-400";
    if (latency < 1000) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const networkConfig = getNetworkConfig();
  const healthConfig = getHealthConfig();

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${networkConfig.bgColor} ${networkConfig.borderColor} ${networkConfig.textColor}`}
    >
      {/* Pulsing indicator dot */}
      <div className="relative">
        <div className={`w-2 h-2 rounded-full ${networkConfig.color}`} />
        {networkStatus === "connected" && (
          <motion.div
            className={`absolute inset-0 w-2 h-2 rounded-full ${networkConfig.color}`}
            animate={{ scale: [1, 1.5, 1], opacity: [0.7, 0, 0.7] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
      </div>

      {/* Icon */}
      {networkConfig.icon}

      {/* Label */}
      <span className="text-sm font-medium">{networkConfig.label}</span>

      {/* Details */}
      {showDetails && networkStatus === "connected" && (
        <>
          <div className="w-px h-4 bg-gray-300 dark:bg-gray-600" />

          {/* Health status */}
          <div className="flex items-center gap-1">
            <svg
              className={`w-3 h-3 ${healthConfig.color}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <span className={`text-xs ${healthConfig.color}`}>
              {healthConfig.label}
            </span>
          </div>

          {/* Latency */}
          {latency !== undefined && (
            <>
              <div className="w-px h-4 bg-gray-300 dark:bg-gray-600" />
              <span className={`text-xs font-mono ${getLatencyColor()}`}>
                {latency}ms
              </span>
            </>
          )}
        </>
      )}
    </div>
  );
}
