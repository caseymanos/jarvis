package com.frontieraudio.heartbeat.speaker

import com.frontieraudio.heartbeat.SpeechSegment

data class VerifiedSpeechSegment(
    val segment: SpeechSegment,
    val similarity: Float,
    val embedding: FloatArray,
    val verifiedAtMillis: Long,
)
