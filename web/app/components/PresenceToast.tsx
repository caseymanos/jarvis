"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export interface PresenceEvent {
  id: string;
  type: "joined" | "left";
  userId: string;
  callSign: string;
  role: string;
  color: string;
  timestamp: number;
}

interface PresenceToastProps {
  events: PresenceEvent[];
  duration?: number;
}

export default function PresenceToast({
  events,
  duration = 3000
}: PresenceToastProps) {
  const [visibleEvents, setVisibleEvents] = useState<PresenceEvent[]>([]);

  useEffect(() => {
    // Add new events to visible list
    const newEvents = events.filter(
      (event) => !visibleEvents.find((v) => v.id === event.id)
    );

    if (newEvents.length > 0) {
      setVisibleEvents([...visibleEvents, ...newEvents]);

      // Remove events after duration
      newEvents.forEach((event) => {
        setTimeout(() => {
          setVisibleEvents((prev) => prev.filter((e) => e.id !== event.id));
        }, duration);
      });
    }
  }, [events]);

  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {visibleEvents.map((event) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: 100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg px-4 py-3 flex items-center gap-3 min-w-[280px]"
          >
            {/* Color indicator */}
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: event.color }}
            />

            {/* Content */}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 dark:text-gray-100">
                  {event.callSign}
                </span>
                {event.role !== "operator" && (
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium">
                    {event.role === "supervisor" ? "SUP" : "OBS"}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {event.type === "joined" ? "joined the session" : "left the session"}
              </p>
            </div>

            {/* Icon */}
            <div className="flex-shrink-0">
              {event.type === "joined" ? (
                <svg
                  className="w-5 h-5 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                  />
                </svg>
              ) : (
                <svg
                  className="w-5 h-5 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 7a4 4 0 11-8 0 4 4 0 018 0zM9 14a6 6 0 00-6 6v1h12v-1a6 6 0 00-6-6z"
                  />
                </svg>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
