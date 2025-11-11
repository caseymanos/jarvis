package com.frontieraudio.heartbeat.speaker

import android.util.Base64
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID

/**
 * Persistent representation of the enrolled user's voice embedding.
 */
data class VoiceProfile(
    val id: String = UUID.randomUUID().toString(),
    val embedding: FloatArray,
    val sampleRateHz: Int,
    val frameSizeSamples: Int,
    val updatedAtMillis: Long,
    val samplesCaptured: Int,
) {

    fun toPreferenceMap(): Map<String, String> {
        return mapOf(
            KEY_ID to id,
            KEY_EMBEDDING to embedding.encodeToBase64(),
            KEY_SAMPLE_RATE to sampleRateHz.toString(),
            KEY_FRAME_SIZE to frameSizeSamples.toString(),
            KEY_UPDATED_AT to updatedAtMillis.toString(),
            KEY_SAMPLE_COUNT to samplesCaptured.toString()
        )
    }

    companion object {
        const val KEY_PREFIX = "voice_profile_"
        const val KEY_ID = "${KEY_PREFIX}id"
        const val KEY_EMBEDDING = "${KEY_PREFIX}embedding"
        const val KEY_SAMPLE_RATE = "${KEY_PREFIX}sample_rate"
        const val KEY_FRAME_SIZE = "${KEY_PREFIX}frame_size"
        const val KEY_UPDATED_AT = "${KEY_PREFIX}updated_at"
        const val KEY_SAMPLE_COUNT = "${KEY_PREFIX}sample_count"

        fun fromPreferences(prefs: Map<String, String>): VoiceProfile? {
            val embeddingString = prefs[KEY_EMBEDDING] ?: return null
            val embedding = embeddingString.decodeFloatArray() ?: return null
            val sampleRate = prefs[KEY_SAMPLE_RATE]?.toIntOrNull() ?: return null
            val frameSize = prefs[KEY_FRAME_SIZE]?.toIntOrNull() ?: return null
            val updatedAt = prefs[KEY_UPDATED_AT]?.toLongOrNull() ?: return null
            val sampleCount = prefs[KEY_SAMPLE_COUNT]?.toIntOrNull() ?: 0
            val id = prefs[KEY_ID] ?: UUID.randomUUID().toString()
            return VoiceProfile(
                id = id,
                embedding = embedding,
                sampleRateHz = sampleRate,
                frameSizeSamples = frameSize,
                updatedAtMillis = updatedAt,
                samplesCaptured = sampleCount
            )
        }

        fun average(embeddings: List<FloatArray>, sampleRateHz: Int, frameSizeSamples: Int, samplesCaptured: Int, nowMillis: Long): VoiceProfile {
            require(embeddings.isNotEmpty()) { "Expected at least one embedding to average" }
            val dimension = embeddings.first().size
            val accumulator = FloatArray(dimension)
            embeddings.forEach { vector ->
                require(vector.size == dimension) { "Embedding dimensions mismatch" }
                for (i in 0 until dimension) {
                    accumulator[i] += vector[i]
                }
            }
            for (i in 0 until dimension) {
                accumulator[i] /= embeddings.size
            }
            return VoiceProfile(
                embedding = accumulator,
                sampleRateHz = sampleRateHz,
                frameSizeSamples = frameSizeSamples,
                updatedAtMillis = nowMillis,
                samplesCaptured = samplesCaptured
            )
        }
    }
}

private fun FloatArray.encodeToBase64(): String {
    val buffer = ByteBuffer.allocate(size * java.lang.Float.BYTES).order(ByteOrder.LITTLE_ENDIAN)
    forEach { buffer.putFloat(it) }
    return Base64.encodeToString(buffer.array(), Base64.NO_WRAP)
}

private fun String.decodeFloatArray(): FloatArray? {
    return try {
        val bytes = Base64.decode(this, Base64.NO_WRAP)
        val floatCount = bytes.size / java.lang.Float.BYTES
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        FloatArray(floatCount) { buffer.getFloat() }
    } catch (t: Throwable) {
        null
    }
}
