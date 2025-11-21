"use client";

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MobileTranscriptMenu } from './MobileTranscriptMenu';
import { useTranscriptDeletion } from '@/app/hooks/useTranscriptDeletion';

interface TranscriptChunk {
  id: string;
  text: string;
  speaker: 'user' | 'agent';
  timestamp: string;
  sequenceNumber: number;
}

interface MobileTranscriptViewProps {
  chunks: TranscriptChunk[];
  onChunkDeleted?: (chunkId: string) => void;
}

export default function MobileTranscriptView({
  chunks,
  onChunkDeleted,
}: MobileTranscriptViewProps) {
  const {
    deleteChunk,
    deletingChunks,
    selectedChunks,
    toggleSelection,
    clearSelection,
    deleteSelected,
    isDeleting,
    isSelected,
    hasSelection,
  } = useTranscriptDeletion({
    onDeleteSuccess: onChunkDeleted,
  });

  const [swipedChunk, setSwipedChunk] = useState<string | null>(null);

  return (
    <div className="mobile-transcript-view h-full flex flex-col">
      {/* Header with selection controls */}
      {hasSelection && (
        <div className="sticky top-0 z-10 bg-blue-600 text-white p-4 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={clearSelection}
                className="p-2 hover:bg-blue-700 rounded-full"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <span className="font-semibold">{selectedChunks.size} selected</span>
            </div>

            <button
              onClick={() => {
                if (confirm(`Delete ${selectedChunks.size} transcripts? This cannot be undone.`)) {
                  deleteSelected();
                }
              }}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 px-4 py-2 rounded-full font-medium"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Transcript list */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence>
          {chunks.map((chunk) => {
            const isChunkSelected = isSelected(chunk.id);
            const isChunkDeleting = isDeleting(chunk.id);

            return (
              <motion.div
                key={chunk.id}
                initial={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ duration: 0.2 }}
                className={`
                  relative border-b border-gray-200 dark:border-gray-700
                  ${isChunkSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-white dark:bg-gray-800'}
                  ${isChunkDeleting ? 'opacity-50' : ''}
                `}
              >
                <div className="p-4">
                  {/* Header row */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {/* Selection checkbox */}
                      {hasSelection && (
                        <button
                          onClick={() => toggleSelection(chunk.id)}
                          className="flex-shrink-0"
                        >
                          <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                            isChunkSelected
                              ? 'bg-blue-600 border-blue-600'
                              : 'border-gray-300 dark:border-gray-600'
                          }`}>
                            {isChunkSelected && (
                              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            )}
                          </div>
                        </button>
                      )}

                      {/* Speaker badge */}
                      <span
                        className={`text-xs font-semibold px-2 py-1 rounded ${
                          chunk.speaker === 'user'
                            ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200'
                            : 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-200'
                        }`}
                      >
                        {chunk.speaker === 'user' ? 'You' : 'Agent'}
                      </span>

                      {/* Timestamp */}
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(chunk.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>

                    {/* Menu */}
                    {!isChunkDeleting && (
                      <MobileTranscriptMenu
                        chunk={chunk}
                        onDelete={deleteChunk}
                        onSelect={hasSelection ? toggleSelection : undefined}
                        isSelected={isChunkSelected}
                      />
                    )}
                  </div>

                  {/* Transcript text */}
                  <p className="text-gray-900 dark:text-gray-100 leading-relaxed text-base">
                    {chunk.text}
                  </p>

                  {/* Deleting overlay */}
                  {isChunkDeleting && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-800/90">
                      <div className="flex items-center gap-2 text-red-600">
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span className="text-sm font-medium">Deleting...</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Swipe indicator hint (shown on first chunk) */}
                {chunk.sequenceNumber === 0 && !hasSelection && (
                  <div className="px-4 pb-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      Long press for options
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Empty state */}
      {chunks.length === 0 && (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <svg className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <p className="text-gray-500 dark:text-gray-400">No transcripts yet</p>
          </div>
        </div>
      )}
    </div>
  );
}
