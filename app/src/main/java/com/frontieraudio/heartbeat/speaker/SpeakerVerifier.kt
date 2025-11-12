package com.frontieraudio.heartbeat.speaker

import ai.picovoice.eagle.Eagle
import ai.picovoice.eagle.EagleException
import ai.picovoice.eagle.EagleProfile
import android.content.Context
import android.util.Log
import com.frontieraudio.heartbeat.BuildConfig
import com.frontieraudio.heartbeat.SpeechSegment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlin.math.ceil

class SpeakerVerifier(context: Context) {

    private val applicationContext = context.applicationContext
    private val recognizerMutex = Mutex()

    private var eagle: Eagle? = null
    private var eagleProfile: EagleProfile? = null
    private var activeProfileId: String? = null
    private var frameLength: Int = 0
    private var sampleRateHz: Int = 0

    suspend fun verify(
        segment: SpeechSegment,
        profile: VoiceProfile,
        threshold: Float
    ): SpeakerVerificationResult = withContext(Dispatchers.Default) {
        try {
            val (similarity, scores) = processSegment(segment, profile)
            if (similarity.isNaN()) {
                SpeakerVerificationResult.Error(null)
            } else if (similarity >= threshold) {
                SpeakerVerificationResult.Match(similarity, scores)
            } else {
                SpeakerVerificationResult.NoMatch(similarity, scores)
            }
        } catch (t: Throwable) {
            Log.e(TAG, "Failed to verify speaker", t)
            SpeakerVerificationResult.Error(t)
        }
    }

    private suspend fun processSegment(
        segment: SpeechSegment,
        profile: VoiceProfile
    ): Pair<Float, FloatArray> = recognizerMutex.withLock {
        Log.d(TAG, "processSegment: segment.id=${segment.id} samples=${segment.samples.size} sampleRate=${segment.sampleRateHz}")
        val recognizer = ensureRecognizer(profile)
        Log.d(TAG, "processSegment: Eagle initialized - frameLength=$frameLength sampleRate=$sampleRateHz")
        
        if (segment.sampleRateHz != sampleRateHz) {
            Log.w(TAG, "Segment sample rate ${segment.sampleRateHz} does not match Eagle requirement $sampleRateHz; skipping segment")
            return 0f to floatArrayOf()
        }
        try {
            recognizer.reset()
        } catch (e: EagleException) {
            Log.w(TAG, "Failed to reset Eagle recognizer", e)
        }
        val localFrameLength = frameLength.takeIf { it > 0 } ?: run {
            Log.e(TAG, "Invalid frameLength: $frameLength")
            return 0f to floatArrayOf()
        }
        if (segment.samples.size < localFrameLength) {
            Log.w(TAG, "Segment too short: ${segment.samples.size} < $localFrameLength")
            return 0f to floatArrayOf()
        }
        val buffer = ShortArray(localFrameLength)
        var index = 0
        var frameIndex = 0
        val skipFrames = calculateLeadInFrameSkip(localFrameLength)
        val allScores = mutableListOf<Float>()
        val scoringScores = mutableListOf<Float>()
        while (index + localFrameLength <= segment.samples.size) {
            segment.samples.copyInto(buffer, 0, index, index + localFrameLength)
            val frameScores = try {
                recognizer.process(buffer)
            } catch (e: EagleException) {
                Log.e(TAG, "Eagle processing failed", e)
                break
            }
            val score = frameScores.firstOrNull() ?: 0f
            allScores.add(score)
            if (frameIndex >= skipFrames) {
                scoringScores.add(score)
            }
            frameIndex++
            index += localFrameLength
        }
        Log.d(
            TAG,
            "processSegment: processed $frameIndex frames (skipped first $skipFrames frames)"
        )
        if (frameIndex == 0) {
            Log.w(TAG, "No frames processed")
            return 0f to floatArrayOf()
        }
        val usableScores = if (scoringScores.isNotEmpty()) scoringScores else allScores
        if (scoringScores.isEmpty()) {
            Log.d(TAG, "processSegment: segment shorter than lead-in skip; using all frames")
        }
        val similarity = computeTrimmedMean(usableScores)
        Log.d(
            TAG,
            "processSegment: final similarity=$similarity (used=${usableScores.size}, totalFrames=$frameIndex)"
        )
        return similarity to allScores.toFloatArray()
    }

    private fun computeTrimmedMean(scores: List<Float>): Float {
        if (scores.isEmpty()) return 0f
        if (scores.size < MIN_TRIMMED_FRAME_COUNT) {
            return scores.average().toFloat()
        }
        val sorted = scores.sorted()
        val trimCount = (sorted.size * TRIM_RATIO).toInt().coerceAtLeast(1)
        val startIndex = trimCount
        val endIndex = sorted.size - trimCount
        val trimmed = if (startIndex < endIndex) sorted.subList(startIndex, endIndex) else sorted
        val trimmedMean = trimmed.average().toFloat()
        Log.d(
            TAG,
            "processSegment: trimmed mean kept ${trimmed.size} of ${sorted.size} frames (trim=$trimCount)"
        )
        return trimmedMean
    }

    private fun calculateLeadInFrameSkip(frameLength: Int): Int {
        if (LEAD_IN_SKIP_MS <= 0) return 0
        if (sampleRateHz <= 0) return 0
        val samplesToSkip = sampleRateHz * (LEAD_IN_SKIP_MS / 1000.0)
        return ceil(samplesToSkip / frameLength.toDouble()).toInt()
    }

    private suspend fun ensureRecognizer(profile: VoiceProfile): Eagle {
        val accessKey = requireAccessKey()
        if (profile.profileBytes.isEmpty()) {
            throw IllegalArgumentException("Voice profile payload is empty")
        }
        return if (activeProfileId == profile.id && eagle != null) {
            eagle!!
        } else {
            eagle?.delete()
            eagleProfile?.delete()

            val newProfile = EagleProfile(profile.profileBytes)
            val newRecognizer = Eagle.Builder()
                .setAccessKey(accessKey)
                .setSpeakerProfile(newProfile)
                .build(applicationContext)

            eagle = newRecognizer
            eagleProfile = newProfile
            activeProfileId = profile.id
            frameLength = newRecognizer.frameLength
            sampleRateHz = newRecognizer.sampleRate
            Log.i(TAG, "Initialized Eagle recognizer frameLength=$frameLength sampleRate=$sampleRateHz")
            newRecognizer
        }
    }

    private fun requireAccessKey(): String {
        val accessKey = BuildConfig.PICOVOICE_ACCESS_KEY
        require(accessKey.isNotBlank()) { "PICOVOICE_ACCESS_KEY is empty. Provide a valid Picovoice AccessKey." }
        return accessKey
    }

    fun close() {
        runBlocking {
            recognizerMutex.withLock {
                eagle?.delete()
                eagle = null
                eagleProfile?.delete()
                eagleProfile = null
                activeProfileId = null
            }
        }
    }

    companion object {
        private const val TAG = "SpeakerVerifier"
        private const val LEAD_IN_SKIP_MS = 250
        private const val TRIM_RATIO = 0.10f
        private const val MIN_TRIMMED_FRAME_COUNT = 8
    }
}
