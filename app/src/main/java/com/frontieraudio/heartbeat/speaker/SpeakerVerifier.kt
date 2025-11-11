package com.frontieraudio.heartbeat.speaker

import android.util.Log
import com.frontieraudio.heartbeat.SpeechSegment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.vosk.Recognizer

class SpeakerVerifier(
    context: android.content.Context,
    private val speakerModelProvider: SpeakerModelProvider = SpeakerModelProvider(context.applicationContext),
    private val speechModelProvider: SpeechModelProvider = SpeechModelProvider(context.applicationContext)
) {

    suspend fun verify(
        segment: SpeechSegment,
        profile: VoiceProfile,
        threshold: Float
    ): SpeakerVerificationResult = withContext(Dispatchers.Default) {
        try {
            val embedding = computeEmbedding(segment) ?: return@withContext SpeakerVerificationResult.Error(null)
            val similarity = cosineSimilarity(embedding, profile.embedding)
            if (similarity >= threshold) {
                SpeakerVerificationResult.Match(similarity, embedding)
            } else {
                SpeakerVerificationResult.NoMatch(similarity, embedding)
            }
        } catch (t: Throwable) {
            Log.e(TAG, "Failed to verify speaker", t)
            SpeakerVerificationResult.Error(t)
        }
    }

    suspend fun computeEmbedding(segment: SpeechSegment): FloatArray? = withContext(Dispatchers.IO) {
        val speakerModel = speakerModelProvider.getModel()
        val speechModel = speechModelProvider.getModel()
        Recognizer(speechModel, segment.sampleRateHz.toFloat(), speakerModel).use { recognizer ->
            recognizer.acceptWaveForm(segment.samples, segment.samples.size)
            val speakerResultJson = recognizer.finalResult
            if (speakerResultJson.isNullOrBlank()) {
                Log.w(TAG, "Empty speaker result from recognizer")
                return@use null
            }
            parseEmbedding(speakerResultJson)
        }
    }

    fun cosineSimilarity(current: FloatArray, reference: FloatArray): Float {
        require(current.size == reference.size) { "Embedding size mismatch" }
        var dot = 0.0
        var normCurrent = 0.0
        var normReference = 0.0
        for (i in current.indices) {
            val a = current[i].toDouble()
            val b = reference[i].toDouble()
            dot += a * b
            normCurrent += a * a
            normReference += b * b
        }
        val denominator = kotlin.math.sqrt(normCurrent) * kotlin.math.sqrt(normReference)
        if (denominator == 0.0) return 0f
        return (dot / denominator).toFloat()
    }

    fun close() {
        speakerModelProvider.clearCachedModel()
        speechModelProvider.clearCachedModel()
    }

    companion object {
        private const val TAG = "SpeakerVerifier"

        private fun parseEmbedding(json: String): FloatArray? {
            return try {
                val root = JSONObject(json)
                if (!root.has("spk")) return null
                val array = root.get("spk")
                val values: JSONArray = when (array) {
                    is JSONArray -> array
                    is String -> JSONArray(array)
                    else -> return null
                }
                FloatArray(values.length()) { index ->
                    values.getDouble(index).toFloat()
                }
            } catch (t: Throwable) {
                Log.e(TAG, "Failed to parse speaker embedding", t)
                null
            }
        }

    }
}
