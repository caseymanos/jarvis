"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CursorPosition {
  user_id: string;
  call_sign: string;
  color: string;
  role: string;
  x: number;
  y: number;
  timestamp: string;
}

interface CollaborativeCursorsProps {
  cursors: Map<string, CursorPosition>;
  containerRef?: React.RefObject<HTMLElement>;
}

export default function CollaborativeCursors({ cursors, containerRef }: CollaborativeCursorsProps) {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef?.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      } else {
        setDimensions({ width: window.innerWidth, height: window.innerHeight });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [containerRef]);

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      <AnimatePresence>
        {Array.from(cursors.entries()).map(([userId, cursor]) => {
          // Convert normalized coordinates to pixels
          const pixelX = cursor.x * dimensions.width;
          const pixelY = cursor.y * dimensions.height;

          return (
            <motion.div
              key={userId}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.15 }}
              style={{
                position: 'absolute',
                left: pixelX,
                top: pixelY,
                transform: 'translate(-4px, -4px)',
              }}
            >
              {/* Cursor pointer */}
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                style={{
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
                }}
              >
                <path
                  d="M5.65376 12.3673L14.3303 15.0903L9.31893 19.3589C8.84274 19.7563 8.14334 19.6974 7.73904 19.2244L5.22499 16.2503C4.82428 15.7812 4.88123 15.0827 5.35377 14.6854L5.65376 12.3673Z"
                  fill={cursor.color}
                />
                <path
                  d="M5.65376 12.3673L14.3303 15.0903L9.31893 19.3589C8.84274 19.7563 8.14334 19.6974 7.73904 19.2244L5.22499 16.2503C4.82428 15.7812 4.88123 15.0827 5.35377 14.6854L5.65376 12.3673Z"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>

              {/* User label */}
              <div
                className="absolute left-6 top-0 whitespace-nowrap"
                style={{
                  backgroundColor: cursor.color,
                  color: 'white',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: '600',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                }}
              >
                <div className="flex items-center gap-1.5">
                  <span>{cursor.call_sign}</span>
                  {cursor.role === 'supervisor' && (
                    <span
                      className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded"
                      style={{
                        backgroundColor: 'rgba(255,255,255,0.3)',
                      }}
                    >
                      SUP
                    </span>
                  )}
                  {cursor.role === 'observer' && (
                    <span
                      className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded"
                      style={{
                        backgroundColor: 'rgba(255,255,255,0.3)',
                      }}
                    >
                      OBS
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
