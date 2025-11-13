package com.frontieraudio.heartbeat.metrics

import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Button
import android.widget.TextView
import android.widget.ScrollView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.frontieraudio.heartbeat.HeartbeatService
import com.frontieraudio.heartbeat.R
import kotlinx.coroutines.isActive
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class MetricsActivity : AppCompatActivity() {

    private lateinit var metricsTitle: TextView
    private lateinit var aggregateStatsText: TextView
    private lateinit var liveMetricsText: TextView
    private lateinit var metricsScrollView: ScrollView
    private lateinit var refreshButton: Button
    private lateinit var clearButton: Button
    private lateinit var exportButton: Button

    private var updateJob: kotlinx.coroutines.Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_metrics)
        
        setupActionBar()
        bindViews()
        configureButtons()
        startLiveUpdates()
        refreshMetrics()
    }

    override fun onDestroy() {
        super.onDestroy()
        updateJob?.cancel()
    }

    private fun setupActionBar() {
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            setDisplayShowHomeEnabled(true)
            title = "Transcription Metrics"
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                finish()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun bindViews() {
        metricsTitle = findViewById(R.id.metricsTitle)
        aggregateStatsText = findViewById(R.id.aggregateStatsText)
        liveMetricsText = findViewById(R.id.liveMetricsText)
        metricsScrollView = findViewById(R.id.metricsScrollView)
        refreshButton = findViewById(R.id.refreshButton)
        clearButton = findViewById(R.id.clearButton)
        exportButton = findViewById(R.id.exportButton)
    }

    private fun configureButtons() {
        refreshButton.setOnClickListener {
            refreshMetrics()
        }

        clearButton.setOnClickListener {
            clearMetrics()
        }

        exportButton.setOnClickListener {
            exportMetrics()
        }
    }

    private fun startLiveUpdates() {
        updateJob = lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (isActive) {
                    refreshMetrics()
                    delay(1000) // Update every second
                }
            }
        }
    }

    private fun refreshMetrics() {
        val service = HeartbeatService.getInstance()
        if (service == null) {
            liveMetricsText.text = "Service not available"
            return
        }

        val collector = service.getMetricsCollector()
        val metrics = collector.getCompleted()
        val aggregate = collector.getAggregateStats()
        val activeCount = collector.getActiveTrackingCount()
        val activeIds = collector.getActiveSegmentIds()

        // Update title with active tracking info
        val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        metricsTitle.text = "Latency Metrics ($timestamp) - Active: $activeCount"

        // Update aggregate stats
        val aggregateDisplay = buildString {
            aggregate?.let { stats ->
                appendLine("=== Aggregate Statistics ===")
                appendLine("Total Transcriptions: ${stats.count}")
                appendLine("Average Latency: ${String.format(Locale.US, "%.1f", stats.avgLatencyMs)}ms")
                appendLine("Min/Max Latency: ${stats.minLatencyMs}ms / ${stats.maxLatencyMs}ms")
                appendLine("Average RTF: ${String.format(Locale.US, "%.2f", stats.avgRTF)}x")
                appendLine()
                appendLine("Pipeline Breakdown:")
                appendLine("  VAD: ${String.format(Locale.US, "%.1f", stats.avgVadMs)}ms")
                appendLine("  Stage2 (Verification): ${String.format(Locale.US, "%.1f", stats.avgStage2Ms)}ms")
                appendLine("  Stage3 (Transcription): ${String.format(Locale.US, "%.1f", stats.avgStage3Ms)}ms")
                appendLine()
                appendLine("Verification Pass Rate: ${String.format(Locale.US, "%.1f", stats.passRate * 100)}%")
                appendLine("Total Words: ${stats.totalWords}")
                appendLine("Total Audio Duration: ${String.format(Locale.US, "%.1f", stats.totalAudioMs / 1000.0)}s")
            } ?: run {
                appendLine("No metrics collected yet.")
                appendLine("Start speaking to collect latency metrics!")
                if (activeCount > 0) {
                    appendLine()
                    appendLine("Currently tracking: $activeCount segments")
                    appendLine("Active segment IDs: ${activeIds.joinToString()}")
                    appendLine("Waiting for transcription to complete...")
                }
            }
        }
        aggregateStatsText.text = aggregateDisplay

        // Update live metrics display
        val liveDisplay = buildString {
            if (metrics.isNotEmpty()) {
                appendLine("=== Recent Transcriptions ===")
                appendLine()
                
                // Show the most recent 10 transcriptions
                metrics.takeLast(10).reversed().forEachIndexed { index, m ->
                    appendLine("📊 #${metrics.size - index}")
                    appendLine("   Transcript: \"${m.transcript}\"")
                    appendLine("   Latency: ${m.totalLatencyMs}ms (RTF: ${String.format(Locale.US, "%.2f", m.realTimeFactor)}x)")
                    appendLine("   VAD: ${m.vadLatencyMs}ms | Stage2: ${m.stage2LatencyMs}ms | Stage3: ${m.stage3LatencyMs}ms")
                    if (m.stage3FirstPartialMs != null) {
                        val timeToFirstPartial = m.stage3FirstPartialMs!! - m.stage3StartMs
                        appendLine("   Time to first partial: ${timeToFirstPartial}ms")
                    }
                    appendLine("   Words: ${m.wordCount} | Verified: ${if (m.verificationPassed) "✅" else "❌"}")
                    if (m.verificationSimilarity != null && m.verificationThreshold != null) {
                        appendLine("   Similarity: ${String.format(Locale.US, "%.3f", m.verificationSimilarity)} (threshold: ${String.format(Locale.US, "%.3f", m.verificationThreshold)})")
                    }
                    appendLine("─".repeat(50))
                    appendLine()
                }
            } else {
                appendLine("No transcriptions completed yet.")
                appendLine()
                appendLine("📊 Metrics collection will show:")
                appendLine("  • Total latency (time from speech start to transcript)")
                appendLine("  • Real-time factor (RTF) - processing speed relative to real-time")
                appendLine("  • Pipeline stage breakdown (VAD, Verification, Transcription)")
                appendLine("  • Time to first partial transcript")
                appendLine("  • Word count and verification results")
                appendLine()
                appendLine("Check live logs with:")
                appendLine("  adb logcat | grep '📊'")
            }
        }
        liveMetricsText.text = liveDisplay

        // Auto-scroll to top for aggregate stats
        metricsScrollView.post {
            metricsScrollView.scrollTo(0, 0)
        }
    }

    private fun clearMetrics() {
        val service = HeartbeatService.getInstance()
        if (service != null) {
            service.getMetricsCollector().clear()
            refreshMetrics()
        }
    }

    private fun exportMetrics() {
        val service = HeartbeatService.getInstance()
        if (service != null) {
            val csv = service.getMetricsCollector().exportCsv()
            // You could implement file sharing or save to external storage here
            // For now, just log it
            android.util.Log.d("MetricsActivity", "CSV Export:\n$csv")
            
            // Show a toast or message that metrics have been exported
            android.widget.Toast.makeText(this, "Metrics exported to logcat", android.widget.Toast.LENGTH_SHORT).show()
        }
    }
}
