package com.frontieraudio.heartbeat

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.cardview.widget.CardView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.frontieraudio.heartbeat.diagnostics.DiagnosticsEvent
import com.frontieraudio.heartbeat.speaker.SpeakerVerificationConfig
import com.frontieraudio.heartbeat.speaker.SpeakerVerificationConfigStore
import com.frontieraudio.heartbeat.speaker.VoiceProfileStore
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.Job
import java.util.Locale
import kotlin.math.roundToInt
import kotlin.math.sqrt

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var openEnrollmentButton: Button
    private lateinit var clearEnrollmentButton: Button
    private lateinit var thresholdSeekBar: SeekBar
    private lateinit var thresholdValue: TextView
    private lateinit var retentionSeekBar: SeekBar
    private lateinit var retentionValue: TextView
    private lateinit var cooldownSeekBar: SeekBar
    private lateinit var cooldownValue: TextView
    private lateinit var verificationCard: CardView
    private lateinit var verificationStatusText: TextView
    private lateinit var verificationSimilarityText: TextView
    private lateinit var verificationCountdownText: TextView
    private lateinit var verificationDiagnosticsText: TextView
    private lateinit var calibrationButton: Button
    private lateinit var calibrationStatusText: TextView

    private val voiceProfileStore by lazy { (application as HeartbeatApplication).voiceProfileStore }
    private val configStore by lazy { (application as HeartbeatApplication).configStore }

    private var baseStatusMessage: String = ""
    private var profileStatusMessage: String = ""
    private var latestConfig: SpeakerVerificationConfig = SpeakerVerificationConfig()

    private var audioEffectsWarning: String? = null
    private var latestSegmentDiagnostics: SegmentDiagnosticsUi? = null
    private var calibrationActive = false
    private var calibrationSuggestion: Float? = null
    private val calibrationSamples = mutableListOf<Float>()

    private var updatingThresholdFromConfig = false
    private var updatingRetentionFromConfig = false
    private var updatingCooldownFromConfig = false
    private var verificationStateJob: Job? = null
    private var countdownJob: Job? = null

    private val recordAudioPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                startHeartbeatService()
                updateStatusText(getString(R.string.foreground_notification_text))
                requestNotificationPermissionIfNeeded()
            } else {
                updateStatusText(getString(R.string.permission_denied_message))
            }
        }

    private val postNotificationsPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (!granted && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                updateStatusText(getString(R.string.notifications_permission_denied))
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        bindViews()
        configureSeekBars()
        configureButtons()
        observeStores()
        observeVerificationState()
        ensurePermissionThenStart()
    }

    override fun onResume() {
        super.onResume()
        ensurePermissionThenStart()
    }

    private fun bindViews() {
        statusText = findViewById(R.id.statusText)
        openEnrollmentButton = findViewById(R.id.openEnrollmentButton)
        clearEnrollmentButton = findViewById(R.id.clearEnrollmentButton)
        thresholdSeekBar = findViewById(R.id.thresholdSeekBar)
        thresholdValue = findViewById(R.id.thresholdValue)
        retentionSeekBar = findViewById(R.id.retentionSeekBar)
        retentionValue = findViewById(R.id.retentionValue)
        cooldownSeekBar = findViewById(R.id.cooldownSeekBar)
        cooldownValue = findViewById(R.id.cooldownValue)
        verificationCard = findViewById(R.id.verificationCard)
        verificationStatusText = findViewById(R.id.verificationStatusText)
        verificationSimilarityText = findViewById(R.id.verificationSimilarityText)
        verificationCountdownText = findViewById(R.id.verificationCountdownText)
        verificationDiagnosticsText = findViewById(R.id.verificationDiagnosticsText)
        verificationDiagnosticsText.isVisible = false
        calibrationButton = findViewById(R.id.calibrationButton)
        calibrationStatusText = findViewById(R.id.calibrationStatus)
        calibrationStatusText.isVisible = false
        updateVerificationIndicator(HeartbeatService.VerificationState(false, null, null))
    }

    private fun configureButtons() {
        openEnrollmentButton.setOnClickListener {
            startActivity(Intent(this, EnrollmentActivity::class.java))
        }
        clearEnrollmentButton.setOnClickListener {
            lifecycleScope.launch {
                voiceProfileStore.clearVoiceProfile()
            }
        }
        calibrationButton.setOnClickListener {
            when {
                calibrationActive -> cancelCalibration(showMessage = true)
                calibrationSuggestion != null -> applyCalibrationSuggestion()
                else -> startCalibration()
            }
        }
    }

    private fun configureSeekBars() {
        thresholdSeekBar.max = THRESHOLD_PROGRESS_STEPS
        thresholdSeekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = thresholdValueFor(progress)
                updateThresholdValue(value)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit

            override fun onStopTrackingTouch(seekBar: SeekBar) {
                if (updatingThresholdFromConfig) return
                val value = thresholdValueFor(seekBar.progress)
                lifecycleScope.launch {
                    configStore.updateMatchThreshold(value)
                }
            }
        })

        retentionSeekBar.max = RETENTION_PROGRESS_MAX
        retentionSeekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val millis = retentionMillisFor(progress)
                updateRetentionValue(millis)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit

            override fun onStopTrackingTouch(seekBar: SeekBar) {
                if (updatingRetentionFromConfig) return
                val newRetention = retentionMillisFor(seekBar.progress)
                lifecycleScope.launch {
                    configStore.updateTiming(
                        positiveRetention = newRetention,
                        negativeCooldown = latestConfig.negativeCooldownMillis
                    )
                }
            }
        })

        cooldownSeekBar.max = COOLDOWN_PROGRESS_MAX
        cooldownSeekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val millis = cooldownMillisFor(progress)
                updateCooldownValue(millis)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit

            override fun onStopTrackingTouch(seekBar: SeekBar) {
                if (updatingCooldownFromConfig) return
                val newCooldown = cooldownMillisFor(seekBar.progress)
                lifecycleScope.launch {
                    configStore.updateTiming(
                        positiveRetention = latestConfig.positiveRetentionMillis,
                        negativeCooldown = newCooldown
                    )
                }
            }
        })
    }

    private fun observeStores() {
        lifecycleScope.launch {
            voiceProfileStore.voiceProfileFlow.collectLatest { profile ->
                Log.d("MainActivity", "Received profile emission: ${if (profile != null) "loaded (${profile.samplesCaptured} samples)" else "null"}")
                profileStatusMessage = if (profile != null) {
                    val details = getString(
                        R.string.profile_enrolled_details,
                        profile.engineVersion.ifBlank { "-" },
                        profile.samplesCaptured
                    )
                    listOf(getString(R.string.profile_enrolled), details).joinToString(separator = "\n")
                } else {
                    getString(R.string.profile_not_enrolled)
                }
                clearEnrollmentButton.isEnabled = profile != null
                calibrationButton.isEnabled = profile != null
                if (profile == null) {
                    cancelCalibration(showMessage = false)
                }
                renderStatus()
            }
        }

        lifecycleScope.launch {
            configStore.config.collectLatest { config ->
                latestConfig = config
                updatingThresholdFromConfig = true
                val thresholdProgress = thresholdProgressFor(config.matchThreshold)
                thresholdSeekBar.progress = thresholdProgress
                updateThresholdValue(config.matchThreshold)
                updatingThresholdFromConfig = false

                updatingRetentionFromConfig = true
                val retentionProgress = retentionProgressFor(config.positiveRetentionMillis)
                retentionSeekBar.progress = retentionProgress
                updateRetentionValue(config.positiveRetentionMillis)
                updatingRetentionFromConfig = false

                updatingCooldownFromConfig = true
                val cooldownProgress = cooldownProgressFor(config.negativeCooldownMillis)
                cooldownSeekBar.progress = cooldownProgress
                updateCooldownValue(config.negativeCooldownMillis)
                updatingCooldownFromConfig = false
            }
        }
    }

    private fun observeVerificationState() {
        verificationStateJob?.cancel()
        verificationStateJob = lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                updateVerificationIndicator(HeartbeatService.VerificationState(false, null, null))
                clearDiagnostics()
                var activeService: HeartbeatService? = null
                var stateCollector: Job? = null
                var diagnosticsCollector: Job? = null
                try {
                    while (isActive) {
                        val service = HeartbeatService.getInstance()
                        when {
                            service != null && service !== activeService -> {
                                stateCollector?.cancel()
                                diagnosticsCollector?.cancel()
                                activeService = service
                                stateCollector = launch {
                                    service.verificationStateFlow().collectLatest { state ->
                                        updateVerificationIndicator(state)
                                    }
                                }
                                diagnosticsCollector = launch {
                                    service.diagnosticsFlow().collectLatest { event ->
                                        handleDiagnosticsEvent(event)
                                    }
                                }
                            }
                            service == null && activeService != null -> {
                                stateCollector?.cancel()
                                diagnosticsCollector?.cancel()
                                stateCollector = null
                                diagnosticsCollector = null
                                activeService = null
                                updateVerificationIndicator(HeartbeatService.VerificationState(false, null, null))
                                clearDiagnostics()
                            }
                        }
                        delay(SERVICE_RETRY_DELAY_MS)
                    }
                } finally {
                    stateCollector?.cancel()
                    diagnosticsCollector?.cancel()
                }
            }
        }
    }

    private fun ensurePermissionThenStart() {
        val statusText = if (isRecordAudioGranted()) {
            startHeartbeatService()
            requestNotificationPermissionIfNeeded()
            getString(R.string.foreground_notification_text)
        } else {
            recordAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            getString(R.string.requesting_permission_message)
        }
        updateStatusText(statusText)
    }

    private fun isRecordAudioGranted(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun startHeartbeatService() {
        HeartbeatService.start(this)
    }

    private fun updateStatusText(message: String) {
        baseStatusMessage = message
        renderStatus()
    }

    private fun renderStatus() {
        val segments = buildList {
            if (baseStatusMessage.isNotBlank()) add(baseStatusMessage)
            if (profileStatusMessage.isNotBlank()) add(profileStatusMessage)
        }
        statusText.text = segments.joinToString(separator = "\n")
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        postNotificationsPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    private fun updateThresholdValue(value: Float) {
        thresholdValue.text = String.format(Locale.US, "%.2f", value)
    }

    private fun updateRetentionValue(millis: Long) {
        retentionValue.text = String.format(Locale.US, "%.1f s", millis / 1000f)
    }

    private fun updateCooldownValue(millis: Long) {
        cooldownValue.text = String.format(Locale.US, "%.1f s", millis / 1000f)
    }

    private fun updateVerificationIndicator(state: HeartbeatService.VerificationState) {
        val isVerified = state.isVerified
        val backgroundColorRes = if (isVerified) {
            R.color.verification_active
        } else {
            R.color.verification_inactive
        }

        verificationCard.setCardBackgroundColor(ContextCompat.getColor(this, backgroundColorRes))
        verificationStatusText.text = getString(
            if (isVerified) R.string.verification_active else R.string.verification_listening
        )

        val similarityValue = state.similarity ?: 0f
        verificationSimilarityText.text = getString(R.string.verification_similarity, similarityValue)

        if (isVerified && state.validUntilElapsedRealtimeMs != null) {
            startCountdownTimer(state.validUntilElapsedRealtimeMs)
        } else {
            cancelCountdownTimer()
        }
    }

    private fun startCountdownTimer(validUntilMs: Long) {
        countdownJob?.cancel()
        val job = lifecycleScope.launch {
            while (isActive) {
                val remainingMs = validUntilMs - SystemClock.elapsedRealtime()
                if (remainingMs <= 0) {
                    verificationCountdownText.text = getString(R.string.verification_expired)
                    break
                }
                val remainingSeconds = remainingMs / 1000f
                verificationCountdownText.text =
                    getString(R.string.verification_countdown, remainingSeconds)
                delay(COUNTDOWN_UPDATE_INTERVAL_MS)
            }
        }
        job.invokeOnCompletion {
            if (countdownJob === job) {
                countdownJob = null
            }
        }
        countdownJob = job
    }

    private fun cancelCountdownTimer() {
        countdownJob?.cancel()
        countdownJob = null
        verificationCountdownText.text = ""  // Empty instead of "Expired"
    }

    override fun onDestroy() {
        verificationStateJob?.cancel()
        verificationStateJob = null
        countdownJob?.cancel()
        countdownJob = null
        super.onDestroy()
    }

    private fun handleDiagnosticsEvent(event: DiagnosticsEvent) {
        when (event) {
            is DiagnosticsEvent.AudioEffectsWarning -> {
                if (event.source == DiagnosticsEvent.Source.VERIFICATION) {
                    audioEffectsWarning = if (event.activeEffects.isEmpty()) {
                        null
                    } else {
                        getString(R.string.diagnostics_audio_effects, event.activeEffects.joinToString())
                    }
                }
            }
            is DiagnosticsEvent.SegmentMetrics -> {
                if (event.source == DiagnosticsEvent.Source.VERIFICATION) {
                    val summary = getString(
                        R.string.diagnostics_segment_metrics,
                        event.rmsDbfs,
                        event.clippingRatio * 100f,
                        event.speechRatio * 100f
                    )
                    latestSegmentDiagnostics = SegmentDiagnosticsUi(summary, event.warnings)
                    handleCalibrationSegment(event)
                }
            }
        }
        updateDiagnosticsText()
    }

    private fun handleCalibrationSegment(event: DiagnosticsEvent.SegmentMetrics) {
        if (!calibrationActive) return
        val similarity = event.similarity ?: return
        if (event.matched == true) {
            calibrationStatusText.isVisible = true
            calibrationStatusText.text = getString(R.string.calibration_status_matched, similarity)
            return
        }
        recordCalibrationSample(similarity)
    }

    private fun startCalibration() {
        calibrationActive = true
        calibrationSamples.clear()
        calibrationSuggestion = null
        calibrationButton.text = getString(R.string.calibration_button_cancel)
        calibrationStatusText.isVisible = true
        calibrationStatusText.text = getString(R.string.calibration_status_start, CALIBRATION_TARGET_SAMPLES)
    }

    private fun cancelCalibration(showMessage: Boolean) {
        val wasActive = calibrationActive || calibrationSuggestion != null
        calibrationActive = false
        calibrationSuggestion = null
        calibrationSamples.clear()
        calibrationButton.text = getString(R.string.calibration_button_start)
        if (showMessage && wasActive) {
            calibrationStatusText.isVisible = true
            calibrationStatusText.text = getString(R.string.calibration_status_cancelled)
        } else {
            calibrationStatusText.isVisible = false
        }
    }

    private fun recordCalibrationSample(similarity: Float) {
        if (!calibrationActive) return
        calibrationSamples.add(similarity)
        calibrationStatusText.isVisible = true
        calibrationStatusText.text = getString(
            R.string.calibration_status_progress,
            calibrationSamples.size,
            CALIBRATION_TARGET_SAMPLES,
            similarity
        )
        if (calibrationSamples.size >= CALIBRATION_TARGET_SAMPLES) {
            finishCalibration()
        }
    }

    private fun finishCalibration() {
        calibrationActive = false
        if (calibrationSamples.isEmpty()) {
            calibrationStatusText.isVisible = false
            calibrationButton.text = getString(R.string.calibration_button_start)
            return
        }
        val mean = calibrationSamples.average().toFloat()
        val variance = calibrationSamples.fold(0f) { acc, sample ->
            val delta = sample - mean
            acc + delta * delta
        } / calibrationSamples.size
        val stdDev = sqrt(variance.toDouble()).toFloat()
        val suggestion = (mean + 3f * stdDev).coerceIn(
            SpeakerVerificationConfig.MIN_THRESHOLD,
            SpeakerVerificationConfig.MAX_THRESHOLD
        )
        calibrationSuggestion = suggestion
        calibrationSamples.clear()
        calibrationButton.text = getString(R.string.calibration_button_apply, suggestion)
        calibrationStatusText.isVisible = true
        calibrationStatusText.text = getString(
            R.string.calibration_status_complete,
            mean,
            stdDev,
            suggestion
        )
    }

    private fun applyCalibrationSuggestion() {
        val suggestion = calibrationSuggestion ?: return
        calibrationActive = false
        calibrationSamples.clear()
        calibrationSuggestion = null
        calibrationButton.text = getString(R.string.calibration_button_start)
        lifecycleScope.launch {
            configStore.updateMatchThreshold(suggestion)
        }
        calibrationStatusText.isVisible = true
        calibrationStatusText.text = getString(R.string.calibration_status_applied, suggestion)
    }

    private fun updateDiagnosticsText() {
        val lines = mutableListOf<String>()
        audioEffectsWarning?.let { lines.add(it) }
        latestSegmentDiagnostics?.let { diagnostics ->
            lines.add(diagnostics.summary)
            if (diagnostics.warnings.isNotEmpty()) {
                lines.add(
                    getString(
                        R.string.diagnostics_warnings_prefix,
                        diagnostics.warnings.joinToString()
                    )
                )
            }
        }
        if (lines.isEmpty()) {
            verificationDiagnosticsText.isVisible = false
            verificationDiagnosticsText.text = ""
            return
        }
        val hasWarnings = audioEffectsWarning != null || (latestSegmentDiagnostics?.warnings?.isNotEmpty() == true)
        val colorRes = if (hasWarnings) R.color.diagnostic_warning else R.color.diagnostic_neutral
        verificationDiagnosticsText.isVisible = true
        verificationDiagnosticsText.setTextColor(ContextCompat.getColor(this, colorRes))
        verificationDiagnosticsText.text = lines.joinToString(separator = "\n")
    }

    private fun clearDiagnostics() {
        audioEffectsWarning = null
        latestSegmentDiagnostics = null
        updateDiagnosticsText()
    }

    private fun thresholdProgressFor(value: Float): Int {
        val clamped = value.coerceIn(
            SpeakerVerificationConfig.MIN_THRESHOLD,
            SpeakerVerificationConfig.MAX_THRESHOLD
        )
        return ((clamped - SpeakerVerificationConfig.MIN_THRESHOLD) * THRESHOLD_SCALE).roundToInt()
    }

    private fun thresholdValueFor(progress: Int): Float {
        val normalized = progress.coerceIn(0, THRESHOLD_PROGRESS_STEPS) / THRESHOLD_SCALE.toFloat()
        return SpeakerVerificationConfig.MIN_THRESHOLD + normalized
    }

    private fun retentionProgressFor(millis: Long): Int {
        val steps = (millis / RETENTION_STEP_MILLIS).toInt()
            .coerceIn(RETENTION_MIN_STEPS, RETENTION_MAX_STEPS)
        return steps - RETENTION_MIN_STEPS
    }

    private fun retentionMillisFor(progress: Int): Long {
        val steps = (RETENTION_MIN_STEPS + progress).coerceIn(RETENTION_MIN_STEPS, RETENTION_MAX_STEPS)
        return steps.toLong() * RETENTION_STEP_MILLIS
    }

    private fun cooldownProgressFor(millis: Long): Int {
        val steps = (millis / COOLDOWN_STEP_MILLIS).toInt()
            .coerceIn(COOLDOWN_MIN_STEPS, COOLDOWN_MAX_STEPS)
        return steps
    }

    private fun cooldownMillisFor(progress: Int): Long {
        val steps = progress.coerceIn(COOLDOWN_MIN_STEPS, COOLDOWN_MAX_STEPS)
        return steps.toLong() * COOLDOWN_STEP_MILLIS
    }

    private data class SegmentDiagnosticsUi(
        val summary: String,
        val warnings: List<String>
    )

    companion object {
        private const val THRESHOLD_SCALE = 100
        private val THRESHOLD_PROGRESS_STEPS =
            ((SpeakerVerificationConfig.MAX_THRESHOLD - SpeakerVerificationConfig.MIN_THRESHOLD) * THRESHOLD_SCALE).roundToInt()
        private const val CALIBRATION_TARGET_SAMPLES = 8

        private const val RETENTION_STEP_MILLIS = 500L
        private const val RETENTION_MIN_STEPS = 2  // 1 second
        private const val RETENTION_MAX_STEPS = 40 // 20 seconds
        private val RETENTION_PROGRESS_MAX = RETENTION_MAX_STEPS - RETENTION_MIN_STEPS

        private const val COOLDOWN_STEP_MILLIS = 500L
        private const val COOLDOWN_MIN_STEPS = 0
        private const val COOLDOWN_MAX_STEPS = 20 // 10 seconds
        private const val COOLDOWN_PROGRESS_MAX = COOLDOWN_MAX_STEPS

        private const val COUNTDOWN_UPDATE_INTERVAL_MS = 100L
        private const val SERVICE_RETRY_DELAY_MS = 500L
    }
}
