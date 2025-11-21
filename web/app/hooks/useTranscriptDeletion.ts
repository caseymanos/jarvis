"use client";

import { useState, useCallback } from 'react';

interface TranscriptChunk {
  id: string;
  text: string;
  speaker: string;
  timestamp: string;
}

interface UseTranscriptDeletionOptions {
  onDeleteSuccess?: (chunkId: string) => void;
  onDeleteError?: (error: Error) => void;
}

export function useTranscriptDeletion({
  onDeleteSuccess,
  onDeleteError,
}: UseTranscriptDeletionOptions = {}) {
  const [deletingChunks, setDeletingChunks] = useState<Set<string>>(new Set());
  const [selectedChunks, setSelectedChunks] = useState<Set<string>>(new Set());

  const deleteChunk = useCallback(async (chunkId: string) => {
    setDeletingChunks(prev => new Set(prev).add(chunkId));

    try {
      const response = await fetch(`/api/transcripts/${chunkId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete transcript');
      }

      const result = await response.json();
      console.log(`✓ Transcript deleted in ${result.deletionTime}ms`);

      // Remove from selection if selected
      setSelectedChunks(prev => {
        const newSet = new Set(prev);
        newSet.delete(chunkId);
        return newSet;
      });

      onDeleteSuccess?.(chunkId);

      return result;
    } catch (error) {
      console.error('Error deleting transcript chunk:', error);
      onDeleteError?.(error as Error);
      throw error;
    } finally {
      setDeletingChunks(prev => {
        const newSet = new Set(prev);
        newSet.delete(chunkId);
        return newSet;
      });
    }
  }, [onDeleteSuccess, onDeleteError]);

  const bulkDelete = useCallback(async (chunkIds: string[]) => {
    if (chunkIds.length === 0) return;

    chunkIds.forEach(id => {
      setDeletingChunks(prev => new Set(prev).add(id));
    });

    try {
      const response = await fetch('/api/transcripts/bulk-delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chunkIds }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to bulk delete transcripts');
      }

      const result = await response.json();
      console.log(`✓ ${result.deletedCount} transcripts deleted in ${result.deletionTime}ms`);

      // Clear selection
      setSelectedChunks(new Set());

      // Call success callback for each deleted chunk
      chunkIds.forEach(id => onDeleteSuccess?.(id));

      return result;
    } catch (error) {
      console.error('Error bulk deleting transcript chunks:', error);
      onDeleteError?.(error as Error);
      throw error;
    } finally {
      chunkIds.forEach(id => {
        setDeletingChunks(prev => {
          const newSet = new Set(prev);
          newSet.delete(id);
          return newSet;
        });
      });
    }
  }, [onDeleteSuccess, onDeleteError]);

  const toggleSelection = useCallback((chunkId: string) => {
    setSelectedChunks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chunkId)) {
        newSet.delete(chunkId);
      } else {
        newSet.add(chunkId);
      }
      return newSet;
    });
  }, []);

  const selectAll = useCallback((chunkIds: string[]) => {
    setSelectedChunks(new Set(chunkIds));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedChunks(new Set());
  }, []);

  const deleteSelected = useCallback(async () => {
    const ids = Array.from(selectedChunks);
    if (ids.length === 0) return;

    await bulkDelete(ids);
  }, [selectedChunks, bulkDelete]);

  return {
    deleteChunk,
    bulkDelete,
    deletingChunks,
    selectedChunks,
    toggleSelection,
    selectAll,
    clearSelection,
    deleteSelected,
    isDeleting: (chunkId: string) => deletingChunks.has(chunkId),
    isSelected: (chunkId: string) => selectedChunks.has(chunkId),
    hasSelection: selectedChunks.size > 0,
  };
}
