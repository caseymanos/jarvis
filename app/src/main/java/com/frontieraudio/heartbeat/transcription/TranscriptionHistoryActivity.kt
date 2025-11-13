package com.frontieraudio.heartbeat.transcription

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Button
import android.widget.TextView
import android.widget.ScrollView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.frontieraudio.heartbeat.HeartbeatService
import com.frontieraudio.heartbeat.R
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class TranscriptionHistoryActivity : AppCompatActivity() {

    private lateinit var historyTitle: TextView
    private lateinit var historyText: TextView
    private lateinit var historyScrollView: ScrollView
    private lateinit var refreshButton: Button
    private lateinit var exportButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_transcription_history)
        
        setupActionBar()
        bindViews()
        configureButtons()
        refreshHistory()
    }

    private fun setupActionBar() {
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            setDisplayShowHomeEnabled(true)
            title = "Transcription History"
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
        historyTitle = findViewById(R.id.historyTitle)
        historyText = findViewById(R.id.historyText)
        historyScrollView = findViewById(R.id.historyScrollView)
        refreshButton = findViewById(R.id.refreshButton)
        exportButton = findViewById(R.id.exportButton)
    }

    private fun configureButtons() {
        refreshButton.setOnClickListener {
            refreshHistory()
        }

        exportButton.setOnClickListener {
            exportToClipboard()
        }
    }

    private fun refreshHistory() {
        val service = HeartbeatService.getInstance()
        if (service == null) {
            historyText.text = "Service not available"
            return
        }

        val transcriptionManager = service.getTranscriptionManager()
        
        lifecycleScope.launch {
            try {
                val transcriptions = transcriptionManager.getAllTranscriptions()
                val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
                historyTitle.text = "Transcription History ($timestamp) - Total: ${transcriptions.size}"

                val display = buildString {
                    if (transcriptions.isEmpty()) {
                        appendLine("No transcriptions saved yet.")
                        appendLine()
                        appendLine("📍 GPS-enabled transcriptions will appear here:")
                        appendLine("  • Complete transcripts with speaker verification")
                        appendLine("  • GPS location data for each transcription")
                        appendLine("  • Timestamps and confidence scores")
                        appendLine("  • Exportable for documentation purposes")
                        appendLine()
                        appendLine("Start speaking to begin recording transcriptions!")
                    } else {
                        appendLine("=== Transcription History ===")
                        appendLine()
                        
                        transcriptions.forEachIndexed { index, record ->
                            val timestamp = SimpleDateFormat("MMM dd, HH:mm:ss", Locale.getDefault()).format(Date(record.timestamp))
                            val gps = record.locationData?.let { 
                                "📍 ${String.format("%.6f", it.latitude)}°, ${String.format("%.6f", it.longitude)}°${it.accuracy?.let { acc -> " (±${acc}m)" } ?: ""}"
                            } ?: "📍 No GPS"
                            val confidence = record.confidence?.let { " (Confidence: ${(it * 100).toInt()}%)" } ?: ""
                            val verified = if (record.isVerified) {
                                "✅ Verified${record.verificationSimilarity?.let { " (${String.format("%.3f", it)})" } ?: ""}"
                            } else {
                                "❌ Not verified"
                            }
                            
                            appendLine("📝 #$${transcriptions.size - index}")
                            appendLine("   🕒 $timestamp")
                            appendLine("   $gps")
                            appendLine("   $verified$confidence")
                            appendLine("   📄 \"${record.transcript}\"")
                            appendLine("─".repeat(60))
                            appendLine()
                        }
                    }
                }

                historyText.text = display
                
                // Auto-scroll to top
                historyScrollView.post {
                    historyScrollView.scrollTo(0, 0)
                }

            } catch (e: Exception) {
                historyText.text = "Error loading transcription history: ${e.message}"
            }
        }
    }

    private fun exportToClipboard() {
        val service = HeartbeatService.getInstance()
        if (service == null) {
            android.widget.Toast.makeText(this, "Service not available", android.widget.Toast.LENGTH_SHORT).show()
            return
        }

        val transcriptionManager = service.getTranscriptionManager()
        
        lifecycleScope.launch {
            try {
                val exported = transcriptionManager.exportTranscriptions()
                
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("Transcription History", exported)
                clipboard.setPrimaryClip(clip)
                
                android.widget.Toast.makeText(this@TranscriptionHistoryActivity, "Transcription history copied to clipboard", android.widget.Toast.LENGTH_SHORT).show()
                
            } catch (e: Exception) {
                android.widget.Toast.makeText(this@TranscriptionHistoryActivity, "Failed to export: ${e.message}", android.widget.Toast.LENGTH_LONG).show()
            }
        }
    }
}
