"use client";

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TranscriptChunk {
  id: string;
  text: string;
  speaker: 'user' | 'agent';
  timestamp: string;
}

interface MobileTranscriptMenuProps {
  chunk: TranscriptChunk;
  onDelete: (chunkId: string) => Promise<void>;
  onSelect?: (chunkId: string) => void;
  isSelected?: boolean;
}

export function MobileTranscriptMenu({
  chunk,
  onDelete,
  onSelect,
  isSelected = false,
}: MobileTranscriptMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const longPressTimer = useRef<NodeJS.Timeout | null>(null);
  const [longPressActive, setLongPressActive] = useState(false);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside as any);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside as any);
    };
  }, [menuOpen]);

  const handleLongPressStart = () => {
    longPressTimer.current = setTimeout(() => {
      setLongPressActive(true);
      setMenuOpen(true);
      // Haptic feedback on supported devices
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    }, 500); // 500ms long press
  };

  const handleLongPressEnd = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
    setLongPressActive(false);
  };

  const handleDelete = async () => {
    if (confirm('Delete this transcript? This cannot be undone.')) {
      setDeleting(true);
      try {
        await onDelete(chunk.id);
        setMenuOpen(false);
      } catch (error) {
        console.error('Failed to delete:', error);
      } finally {
        setDeleting(false);
      }
    }
  };

  const handleSelect = () => {
    onSelect?.(chunk.id);
    setMenuOpen(false);
  };

  return (
    <div ref={menuRef} className="relative">
      {/* Three-dot menu button */}
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        onTouchStart={handleLongPressStart}
        onTouchEnd={handleLongPressEnd}
        onMouseDown={handleLongPressStart}
        onMouseUp={handleLongPressEnd}
        onMouseLeave={handleLongPressEnd}
        className={`
          p-2 rounded-full transition-all
          ${longPressActive ? 'bg-blue-100 dark:bg-blue-900 scale-110' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}
          ${menuOpen ? 'bg-gray-100 dark:bg-gray-700' : ''}
        `}
        aria-label="Open transcript menu"
      >
        <svg className="w-5 h-5 text-gray-600 dark:text-gray-300" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </button>

      {/* Dropdown menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50"
          >
            <div className="py-1">
              {/* Select option */}
              {onSelect && (
                <button
                  onClick={handleSelect}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {isSelected ? 'Deselect' : 'Select'}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      For bulk actions
                    </div>
                  </div>
                </button>
              )}

              {/* Copy text option */}
              <button
                onClick={() => {
                  navigator.clipboard.writeText(chunk.text);
                  setMenuOpen(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Copy Text
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Copy to clipboard
                  </div>
                </div>
              </button>

              {/* Divider */}
              <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

              {/* Delete option */}
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
              >
                {deleting ? (
                  <>
                    <svg className="animate-spin w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <div className="text-sm font-medium text-red-600">
                      Deleting...
                    </div>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    <div>
                      <div className="text-sm font-medium text-red-600">
                        Delete
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Cannot be undone
                      </div>
                    </div>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
