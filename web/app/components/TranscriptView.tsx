"use client";

import { useEffect, useCallback, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranscriptDeletion } from '@/app/hooks/useTranscriptDeletion';

interface TranscriptChunk {
  id: string;
  text: string;
  speaker: 'user' | 'agent';
  timestamp: string;
  sequenceNumber: number;
}

interface TranscriptViewProps {
  chunks: TranscriptChunk[];
  onChunkDeleted?: (chunkId: string) => void;
}

export default function TranscriptView({ chunks, onChunkDeleted }: TranscriptViewProps) {
  const [hoveredChunk, setHoveredChunk] = useState<string | null>(null);
  const [focusedChunk, setFocusedChunk] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    deleteChunk,
    deletingChunks,
    selectedChunks,
    toggleSelection,
    selectAll,
    clearSelection,
    deleteSelected,
    isDeleting,
    isSelected,
    hasSelection,
  } = useTranscriptDeletion({
    onDeleteSuccess: onChunkDeleted,
  });

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Delete key - delete focused or selected chunks
      if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault();

        if (hasSelection) {
          // Delete all selected chunks
          if (confirm(`Delete ${selectedChunks.size} selected transcript chunks? This cannot be undone.`)) {
            deleteSelected();
          }
        } else if (focusedChunk) {
          // Delete focused chunk
          if (confirm('Delete this transcript chunk? This cannot be undone.')) {
            deleteChunk(focusedChunk);
            setFocusedChunk(null);
          }
        }
      }

      // Cmd/Ctrl + A - select all
      if ((event.metaKey || event.ctrlKey) && event.key === 'a') {
        event.preventDefault();
        selectAll(chunks.map(c => c.id));
      }

      // Escape - clear selection
      if (event.key === 'Escape') {
        clearSelection();
        setFocusedChunk(null);
      }

      // Cmd/Ctrl + D - quick delete focused chunk (no confirmation)
      if ((event.metaKey || event.ctrlKey) && event.key === 'd') {
        event.preventDefault();
        if (focusedChunk) {
          deleteChunk(focusedChunk);
          setFocusedChunk(null);
        }
      }

      // Space - toggle selection of focused chunk
      if (event.key === ' ' && focusedChunk && !event.shiftKey) {
        event.preventDefault();
        toggleSelection(focusedChunk);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    chunks,
    focusedChunk,
    hasSelection,
    selectedChunks,
    deleteChunk,
    deleteSelected,
    toggleSelection,
    selectAll,
    clearSelection,
  ]);

  const handleChunkClick = useCallback((chunkId: string, event: React.MouseEvent) => {
    if (event.shiftKey) {
      toggleSelection(chunkId);
    } else {
      setFocusedChunk(chunkId);
    }
  }, [toggleSelection]);

  return (
    <div ref={containerRef} className="transcript-view">
      {/* Keyboard shortcuts help */}
      <div className="sticky top-0 z-10 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-3">
        <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          <div className="flex gap-4">
            <span><kbd className="kbd">⌫</kbd> Delete</span>
            <span><kbd className="kbd">⌘D</kbd> Quick Delete</span>
            <span><kbd className="kbd">⌘A</kbd> Select All</span>
            <span><kbd className="kbd">Esc</kbd> Clear</span>
            <span><kbd className="kbd">Shift+Click</kbd> Multi-select</span>
          </div>
          {hasSelection && (
            <div className="flex items-center gap-2">
              <span className="font-medium">{selectedChunks.size} selected</span>
              <button
                onClick={() => deleteSelected()}
                className="px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-xs"
              >
                Delete Selected
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Transcript chunks */}
      <div className="space-y-2 p-4">
        <AnimatePresence>
          {chunks.map((chunk) => {
            const isFocused = focusedChunk === chunk.id;
            const isChunkSelected = isSelected(chunk.id);
            const isChunkDeleting = isDeleting(chunk.id);

            return (
              <motion.div
                key={chunk.id}
                initial={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ duration: 0.2 }}
                className={`
                  relative group p-4 rounded-lg cursor-pointer transition-all
                  ${isFocused ? 'ring-2 ring-blue-500' : ''}
                  ${isChunkSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500' : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'}
                  ${isChunkDeleting ? 'opacity-50 pointer-events-none' : ''}
                  hover:shadow-md
                `}
                onClick={(e) => handleChunkClick(chunk.id, e)}
                onMouseEnter={() => setHoveredChunk(chunk.id)}
                onMouseLeave={() => setHoveredChunk(null)}
                tabIndex={0}
                onFocus={() => setFocusedChunk(chunk.id)}
              >
                {/* Speaker badge */}
                <div className="flex items-start justify-between mb-2">
                  <span
                    className={`text-xs font-semibold px-2 py-1 rounded ${
                      chunk.speaker === 'user'
                        ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200'
                        : 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-200'
                    }`}
                  >
                    {chunk.speaker === 'user' ? 'You' : 'Agent'}
                  </span>

                  {/* Timestamp and delete button */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(chunk.timestamp).toLocaleTimeString()}
                    </span>

                    {(hoveredChunk === chunk.id || isFocused) && !isChunkDeleting && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm('Delete this transcript chunk? This cannot be undone.')) {
                            deleteChunk(chunk.id);
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                        title="Delete chunk (Delete key)"
                      >
                        <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>

                {/* Transcript text */}
                <p className="text-gray-900 dark:text-gray-100 leading-relaxed">
                  {chunk.text}
                </p>

                {/* Selection indicator */}
                {isChunkSelected && (
                  <div className="absolute top-2 left-2">
                    <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}

                {/* Deleting indicator */}
                {isChunkDeleting && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80 rounded-lg">
                    <div className="flex items-center gap-2 text-red-600">
                      <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span className="text-sm font-medium">Deleting...</span>
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <style jsx>{`
        .kbd {
          padding: 2px 6px;
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-family: monospace;
          font-size: 11px;
        }
      `}</style>
    </div>
  );
}
