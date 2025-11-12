package com.frontieraudio.heartbeat.transcription

import com.frontieraudio.heartbeat.speaker.VerifiedSpeechSegment
import com.frontieraudio.heartbeat.location.LocationData

data class TranscriptionResult(
    val segment: VerifiedSpeechSegment,
    val transcript: String,
    val confidence: Float?,
    val isFinal: Boolean,
    val processingTimeMs: Long,
    val locationData: LocationData?
)

data class TranscriptionConfig(
    val cartesiaApiKey: String,
    val cartesiaUrl: String = "wss://api.cartesia.ai/stt/websocket",
    val language: String = "en",
    val includeTimestamps: Boolean = true,
    val enableLocationTracking: Boolean = true
)