package com.frontieraudio.heartbeat

/**
 * Represents a contiguous block of voiced audio emitted by Stage 1 (VAD).
 *
 * Stage 2 (speaker verification) should treat this as the canonical input:
 * - `samples` is a mono PCM-16 buffer at `sampleRateHz`
 * - `startTimestampNs` / `endTimestampNs` are based on `SystemClock.elapsedRealtimeNanos()`
 * - `frameSizeSamples` indicates the window size used by the VAD
 */
data class SpeechSegment(
    val id: Long,
    val startTimestampNs: Long,
    val endTimestampNs: Long,
    val sampleRateHz: Int,
    val frameSizeSamples: Int,
    val samples: ShortArray,
) {
    val durationMillis: Long
        get() = ((endTimestampNs - startTimestampNs).coerceAtLeast(0L)) / 1_000_000

    val durationSamples: Int
        get() = samples.size
}

