package com.frontieraudio.heartbeat

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Bundle
import android.os.SystemClock
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.frontieraudio.heartbeat.audio.SpeechSegmentAssembler
import com.frontieraudio.heartbeat.speaker.SpeakerVerifier
import com.frontieraudio.heartbeat.speaker.VoiceProfile
import com.frontieraudio.heartbeat.speaker.VoiceProfileStore
import com.konovalov.vad.silero.Vad
import com.konovalov.vad.silero.VadSilero
import com.konovalov.vad.silero.config.FrameSize
import com.konovalov.vad.silero.config.Mode
import com.konovalov.vad.silero.config.SampleRate
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.max

class EnrollmentActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var promptText: TextView
    private lateinit var progressText: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var primaryButton: Button
    private lateinit var cancelButton: Button

    private val voiceProfileStore by lazy { VoiceProfileStore(applicationContext) }
    private val speakerVerifierLazy = lazy { SpeakerVerifier(applicationContext) }
    private val speakerVerifier: SpeakerVerifier
        get() = speakerVerifierLazy.value

    private var recordingJob: Job? = null
    private var collectedEmbeddings = mutableListOf<FloatArray>()
    private var samplesCaptured = 0

    private val audioPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startRecording()
        } else {
            statusText.text = getString(R.string.enrollment_permission_denied)
            setRecordingUi(false)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_enrollment)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        statusText = findViewById(R.id.enrollmentStatus)
        promptText = findViewById(R.id.enrollmentPrompt)
        progressText = findViewById(R.id.enrollmentProgressText)
        progressBar = findViewById(R.id.enrollmentProgressBar)
        primaryButton = findViewById(R.id.enrollmentPrimaryButton)
        cancelButton = findViewById(R.id.enrollmentCancelButton)

        progressBar.max = REQUIRED_SEGMENTS
        progressBar.progress = 0

        primaryButton.setOnClickListener {
            if (recordingJob?.isActive == true) {
                stopRecording()
            } else {
                ensurePermissionThenStart()
            }
        }

        cancelButton.setOnClickListener {
            stopRecording()
            finish()
        }

        updateProgress()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    override fun onStop() {
        super.onStop()
        stopRecording()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (speakerVerifierLazy.isInitialized()) {
            speakerVerifier.close()
        }
    }

    private fun ensurePermissionThenStart() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startRecording()
        } else {
            audioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun startRecording() {
        if (recordingJob?.isActive == true) return
        collectedEmbeddings = mutableListOf()
        samplesCaptured = 0
        statusText.text = getString(R.string.enrollment_listening_status)
        setRecordingUi(true)
        updateProgress()

        recordingJob = lifecycleScope.launch(Dispatchers.IO) {
            val sampleRate = SampleRate.SAMPLE_RATE_16K
            val frameSize = FrameSize.FRAME_SIZE_512
            val audioRecord = createAudioRecord(sampleRate, frameSize)
            val vad = createVad(sampleRate, frameSize)
            val frameBuffer = ShortArray(frameSize.value)
            val assembler = SpeechSegmentAssembler(
                sampleRateHz = sampleRate.value,
                frameSizeSamples = frameSize.value,
                preRollDurationMs = ENROLLMENT_PREROLL_MS,
                minSegmentDurationMs = ENROLLMENT_MIN_SEGMENT_MS
            ) { segment ->
                val embedding = speakerVerifier.computeEmbedding(segment)
                if (embedding != null) {
                    collectedEmbeddings.add(embedding)
                    samplesCaptured += segment.samples.size
                    withContext(Dispatchers.Main) {
                        statusText.text = getString(
                            R.string.enrollment_segment_captured,
                            collectedEmbeddings.size,
                            REQUIRED_SEGMENTS
                        )
                        updateProgress()
                    }
                }
            }

            try {
                audioRecord.startRecording()
                var frameOffset = 0
                while (isActive && collectedEmbeddings.size < REQUIRED_SEGMENTS) {
                    val read = audioRecord.read(
                        frameBuffer,
                        frameOffset,
                        frameBuffer.size - frameOffset,
                        AudioRecord.READ_BLOCKING
                    )
                    if (read < 0) {
                        throw IllegalStateException("AudioRecord read failed with code $read")
                    }
                    if (read == 0) continue
                    frameOffset += read
                    if (frameOffset >= frameBuffer.size) {
                        val frameCopy = frameBuffer.copyOf()
                        val isSpeech = vad.isSpeech(frameBuffer)
                        val timestampNs = SystemClock.elapsedRealtimeNanos()
                        assembler.onFrame(frameCopy, isSpeech, timestampNs)
                        frameOffset = 0
                    }
                }

                if (!isActive) return@launch

                if (collectedEmbeddings.size >= REQUIRED_SEGMENTS) {
                    completeEnrollment()
                } else {
                    withContext(Dispatchers.Main) {
                        statusText.text = getString(R.string.enrollment_incomplete)
                        setRecordingUi(false)
                    }
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                withContext(Dispatchers.Main) {
                    statusText.text = getString(R.string.enrollment_error_generic)
                    setRecordingUi(false)
                }
            } finally {
                try {
                    audioRecord.stop()
                } catch (_: IllegalStateException) {
                }
                audioRecord.release()
                vad.close()
                assembler.reset()
                withContext(NonCancellable + Dispatchers.Main) {
                    if (collectedEmbeddings.size < REQUIRED_SEGMENTS) {
                        setRecordingUi(false)
                    }
                    recordingJob = null
                }
            }
        }
    }

    private suspend fun completeEnrollment() {
        withContext(Dispatchers.Main) {
            statusText.text = getString(R.string.enrollment_processing)
            setRecordingUi(false)
        }
        val profile = VoiceProfile.average(
            embeddings = collectedEmbeddings,
            sampleRateHz = SampleRate.SAMPLE_RATE_16K.value,
            frameSizeSamples = FrameSize.FRAME_SIZE_512.value,
            samplesCaptured = samplesCaptured,
            nowMillis = System.currentTimeMillis()
        )
        voiceProfileStore.saveVoiceProfile(profile)
        withContext(Dispatchers.Main) {
            statusText.text = getString(R.string.enrollment_complete)
            promptText.text = getString(R.string.enrollment_complete_prompt)
            updateProgress()
            primaryButton.text = getString(R.string.enrollment_restart)
        }
    }

    private fun stopRecording() {
        recordingJob?.cancel()
        setRecordingUi(false)
    }

    private fun setRecordingUi(active: Boolean) {
        primaryButton.text = if (active) {
            getString(R.string.enrollment_stop)
        } else {
            getString(R.string.enrollment_start)
        }
        cancelButton.isEnabled = true
    }

    private fun updateProgress() {
        progressBar.progress = collectedEmbeddings.size.coerceAtMost(REQUIRED_SEGMENTS)
        progressText.text = getString(
            R.string.enrollment_progress,
            collectedEmbeddings.size,
            REQUIRED_SEGMENTS
        )
    }

    private fun createAudioRecord(sampleRate: SampleRate, frameSize: FrameSize): AudioRecord {
        val minBuffer = AudioRecord.getMinBufferSize(
            sampleRate.value,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        val bufferSize = max(minBuffer, frameSize.value * BYTES_PER_SAMPLE)
        val audioFormat = AudioFormat.Builder()
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(sampleRate.value)
            .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
            .build()
        return AudioRecord.Builder()
            .setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
            .setAudioFormat(audioFormat)
            .setBufferSizeInBytes(bufferSize)
            .build()
    }

    private fun createVad(sampleRate: SampleRate, frameSize: FrameSize): VadSilero {
        return Vad.builder()
            .setContext(applicationContext)
            .setSampleRate(sampleRate)
            .setFrameSize(frameSize)
            .setMode(Mode.NORMAL)
            .setSpeechDurationMs(VAD_SPEECH_MS)
            .setSilenceDurationMs(VAD_SILENCE_MS)
            .build()
    }

    companion object {
        private const val REQUIRED_SEGMENTS = 3
        private const val ENROLLMENT_MIN_SEGMENT_MS = 800
        private const val ENROLLMENT_PREROLL_MS = 240
        private const val VAD_SPEECH_MS = 60
        private const val VAD_SILENCE_MS = 200
        private const val BYTES_PER_SAMPLE = 2
    }
}
