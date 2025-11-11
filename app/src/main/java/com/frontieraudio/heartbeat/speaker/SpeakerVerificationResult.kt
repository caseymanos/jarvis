package com.frontieraudio.heartbeat.speaker

sealed class SpeakerVerificationResult {
    object NotEnrolled : SpeakerVerificationResult()
    data class Match(val similarity: Float, val embedding: FloatArray) : SpeakerVerificationResult()
    data class NoMatch(val similarity: Float, val embedding: FloatArray) : SpeakerVerificationResult()
    data class Error(val throwable: Throwable?) : SpeakerVerificationResult()
}
