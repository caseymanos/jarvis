package com.frontieraudio.heartbeat.audio

import android.util.Log
import com.frontieraudio.heartbeat.SpeechSegment

class SpeechSegmentAssembler(
    private val sampleRateHz: Int,
    private val frameSizeSamples: Int,
    preRollDurationMs: Int,
    minSegmentDurationMs: Int,
    private val onSegmentReady: suspend (SpeechSegment) -> Unit,
) {

    private val frameDurationNs: Long =
        (frameSizeSamples.toLong() * 1_000_000_000L) / sampleRateHz
    private val preRollFrameCount: Int =
        ((preRollDurationMs.toLong() * sampleRateHz) / (frameSizeSamples * 1_000L))
            .toInt()
            .coerceAtLeast(1)
    private val minSegmentFrameCount: Int =
        ((minSegmentDurationMs.toLong() * sampleRateHz) / (frameSizeSamples * 1_000L))
            .toInt()
            .coerceAtLeast(1)

    private val preRollFrames = ArrayDeque<ShortArray>(preRollFrameCount)
    private var activeFrames: MutableList<ShortArray>? = null
    private var segmentStartNs: Long = 0L
    private var segmentIdCounter: Long = 0L

    suspend fun onFrame(frame: ShortArray, isSpeech: Boolean, frameTimestampNs: Long) {
        if (isSpeech) {
            ensureSegmentStarted(frameTimestampNs)
            activeFrames?.add(frame)
        } else {
            if (activeFrames != null) {
                finishSegment(frameTimestampNs)
            }
            addPreRoll(frame)
        }
    }

    fun reset() {
        preRollFrames.clear()
        activeFrames = null
        segmentStartNs = 0L
    }

    private fun ensureSegmentStarted(frameTimestampNs: Long) {
        if (activeFrames != null) return

        val frames = mutableListOf<ShortArray>()
        if (preRollFrames.isNotEmpty()) {
            frames.addAll(preRollFrames)
            preRollFrames.clear()
        }
        activeFrames = frames
        segmentStartNs = frameTimestampNs - frameDurationNs * frames.size
    }

    private fun addPreRoll(frame: ShortArray) {
        if (preRollFrames.size == preRollFrameCount) {
            preRollFrames.removeFirst()
        }
        preRollFrames.addLast(frame)
    }

    private suspend fun finishSegment(frameTimestampNs: Long) {
        val frames = activeFrames ?: return
        activeFrames = null

        if (minSegmentFrameCount > 0 && frames.size < minSegmentFrameCount) {
            Log.d(TAG, "Dropping short Stage1 segment frames=${frames.size} (min=$minSegmentFrameCount)")
            return
        }

        Log.d(TAG, "Completing Stage1 segment with ${frames.size} frames")
        val totalSamples = frames.sumOf { it.size }
        val merged = ShortArray(totalSamples)
        var offset = 0
        frames.forEach { frame ->
            frame.copyInto(merged, destinationOffset = offset)
            offset += frame.size
        }

        val segmentId = ++segmentIdCounter
        val segment = SpeechSegment(
            id = segmentId,
            startTimestampNs = segmentStartNs,
            endTimestampNs = frameTimestampNs,
            sampleRateHz = sampleRateHz,
            frameSizeSamples = frameSizeSamples,
            samples = merged
        )

        onSegmentReady(segment)
    }

    companion object {
        private const val TAG = "SpeechSegmentAssembler"
    }
}
