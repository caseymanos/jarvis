package com.frontieraudio.heartbeat.transcription

import android.util.Log
import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import com.frontieraudio.heartbeat.SpeechSegment
import com.frontieraudio.heartbeat.speaker.VerifiedSpeechSegment
import com.frontieraudio.heartbeat.location.LocationData
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.TimeUnit

// Data classes for WebSocket streaming protocol
data class WebSocketConfig(
    @JsonProperty("model") val model: String,
    @JsonProperty("language") val language: String?,
    @JsonProperty("encoding") val encoding: String = "pcm_s16le",
    @JsonProperty("sample_rate") val sampleRate: Int = 16000
)

data class EndOfStream(
    @JsonProperty("message") val message: String = "EOS"
)

class CartesiaWebSocketClient(
    private val config: TranscriptionConfig,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
) {
    private val objectMapper = jacksonObjectMapper()
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS) // No timeout for streaming
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var connectionJob: Job? = null
    @Volatile
    private var isConnected = false

    fun isConnected(): Boolean = isConnected

    private val transcriptionResultsInternal = MutableSharedFlow<TranscriptionResult>(
        replay = 0,
        extraBufferCapacity = 10,
        onBufferOverflow = kotlinx.coroutines.channels.BufferOverflow.DROP_OLDEST
    )

    val transcriptionResults: SharedFlow<TranscriptionResult> = transcriptionResultsInternal.asSharedFlow()

    private val webSocketListener = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.i(TAG, "WebSocket connection opened")
            isConnected = true
            sendInitMessage()
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            handleTextMessage(text)
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            Log.w(TAG, "Received unexpected binary message")
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Log.w(TAG, "WebSocket closing: $code - $reason")
            isConnected = false
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.e(TAG, "WebSocket closed: $code - $reason")
            isConnected = false
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e(TAG, "WebSocket failure", t)
            isConnected = false
            connectionJob?.cancel()
            connectionJob = scope.launch {
                delay(RECONNECT_DELAY_MS)
                if (isActive) {
                    Log.i(TAG, "Attempting to reconnect WebSocket...")
                    connect()
                }
            }
        }
    }

    fun connect() {
        if (isConnected) {
            Log.d(TAG, "Already connected")
            return
        }
        val urlWithAuth = "${config.cartesiaUrl}?api_key=${config.cartesiaApiKey}"
        Log.i(TAG, "Connecting to Cartesia WebSocket at $urlWithAuth")
        val request = Request.Builder()
            .url(urlWithAuth)
            .addHeader("Content-Type", "application/json")
            .addHeader("Cartesia-Version", "2025-04-16")
            .build()
        webSocket = client.newWebSocket(request, webSocketListener)
    }

    fun disconnect() {
        connectionJob?.cancel()
        connectionJob = null
        webSocket?.close(1000, "Client disconnect")
        webSocket = null
        isConnected = false
        scope.cancel()
        Log.d(TAG, "Disconnected from Cartesia WebSocket")
    }

    private fun sendInitMessage() {
        try {
            val initConfig = WebSocketConfig(
                model = "ink-whisper",
                language = config.language
            )
            val initJson = objectMapper.writeValueAsString(initConfig)
            webSocket?.send(initJson)
            Log.i(TAG, "Sent WebSocket init message: $initJson")
        } catch (e: Exception) {
            Log.e(TAG, "Error sending WebSocket init message", e)
        }
    }

    private fun handleTextMessage(text: String) {
        Log.i(TAG, "Received WebSocket message: ${text.take(200)}...")
        try {
            val response: CartesiaResponse = objectMapper.readValue(text)
            if (response.text != null) {
                handleTranscriptionResponse(response)
            } else {
                Log.w(TAG, "Received response without text: $text")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing Cartesia response: $text", e)
        }
    }

    private fun handleTranscriptionResponse(response: CartesiaResponse) {
        val fullText = response.segments?.joinToString(" ") { it.text } ?: response.text ?: ""
        Log.i(TAG, "Transcription: '$fullText'")

        val result = TranscriptionResult(
            segment = createDummyVerifiedSegment(),
            transcript = fullText,
            confidence = null,
            isFinal = response.is_final ?: (response.type == "final"),
            processingTimeMs = 0,
            locationData = null
        )
        transcriptionResultsInternal.tryEmit(result)
    }

    fun startTranscriptionSession() {
        scope.launch {
            if (!isConnected) {
                Log.i(TAG, "Session start requested, connecting WebSocket...")
                connect()
            } else {
                Log.d(TAG, "Session start requested, already connected.")
            }
        }
    }

    fun streamAudioChunk(audioChunk: ShortArray) {
        if (!isConnected) {
            Log.w(TAG, "Not connected, cannot stream audio chunk.")
            return
        }
        scope.launch {
            try {
                val byteBuffer = ByteBuffer.allocate(audioChunk.size * 2)
                byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
                for (sample in audioChunk) {
                    byteBuffer.putShort(sample)
                }
                val audioBytes = byteBuffer.array()
                webSocket?.send(ByteString.of(*audioBytes))
                Log.d(TAG, "Sent audio chunk: ${audioBytes.size} bytes")
            } catch (e: Exception) {
                Log.e(TAG, "Error streaming audio chunk", e)
            }
        }
    }

    fun endTranscriptionSession() {
        if (!isConnected) {
            Log.w(TAG, "Not connected, cannot end session.")
            return
        }
        scope.launch {
            try {
                val eosMessage = objectMapper.writeValueAsString(EndOfStream())
                webSocket?.send(eosMessage)
                Log.i(TAG, "Sent End-of-Stream message.")
            } catch (e: Exception) {
                Log.e(TAG, "Error sending end-of-stream message", e)
            }
        }
    }

    private fun createDummyVerifiedSegment(): VerifiedSpeechSegment {
        return VerifiedSpeechSegment(
            segment = SpeechSegment(
                id = -1,
                startTimestampNs = 0L,
                endTimestampNs = 0L,
                sampleRateHz = 16000,
                frameSizeSamples = 512,
                samples = ShortArray(0)
            ),
            similarity = 0f,
            scores = floatArrayOf(),
            verifiedAtMillis = System.currentTimeMillis()
        )
    }

    companion object {
        private const val TAG = "CartesiaWebSocket"
        private const val RECONNECT_DELAY_MS = 5000L
    }
}

// Data classes for JSON serialization/deserialization
data class CartesiaResponse(
    @JsonProperty("text") val text: String?,
    @JsonProperty("segments") val segments: List<TranscriptionSegment>?,
    @JsonProperty("type") val type: String?,
    @JsonProperty("message") val message: String?,
    @JsonProperty("is_final") val is_final: Boolean?
)

data class TranscriptionSegment(
    @JsonProperty("text") val text: String,
    @JsonProperty("start") val start: Float?,
    @JsonProperty("end") val end: Float?
)
