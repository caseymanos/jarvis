package com.frontieraudio.heartbeat.debug

import android.os.Bundle
import android.widget.Button
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class LogViewerActivity : AppCompatActivity() {
    
    private lateinit var logText: TextView
    private lateinit var scrollView: ScrollView
    private lateinit var refreshButton: Button
    private lateinit var clearButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        logText = TextView(this).apply {
            setPadding(16, 16, 16, 16)
            textSize = 12f
            typeface = android.graphics.Typeface.MONOSPACE
        }
        
        scrollView = ScrollView(this).apply {
            layoutParams = android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT
            ).apply { weight = 1f }
            addView(logText)
        }
        
        refreshButton = Button(this).apply {
            text = "Refresh Logs"
            setOnClickListener { refreshLogs() }
        }
        
        clearButton = Button(this).apply {
            text = "Clear Logs"
            setOnClickListener { clearLogs() }
        }
        
        val buttonLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            addView(refreshButton, android.widget.LinearLayout.LayoutParams(
                0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f
            ).apply { setMargins(0, 8, 4, 8) })
            addView(clearButton, android.widget.LinearLayout.LayoutParams(
                0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f
            ).apply { setMargins(4, 8, 0, 8) })
        }
        
        val mainLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            addView(buttonLayout)
            addView(scrollView)
        }
        
        setContentView(mainLayout)
        title = "Heartbeat Logs"
        
        refreshLogs()
    }
    
    private fun refreshLogs() {
        lifecycleScope.launch {
            try {
                logText.text = "Loading in-app logs..."
                
                val logs = AppLogger.getRecentLogs(300)
                val stats = AppLogger.getLogStats()
                
                val displayText = buildString {
                    appendLine("=== HEARTBEAT APP LOGS ===")
                    appendLine("Stats: $stats")
                    appendLine("Last updated: ${java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())}")
                    appendLine()
                    
                    if (logs.isEmpty()) {
                        appendLine("No logs yet. Try speaking to trigger activity!")
                        appendLine()
                        appendLine("Expected activity:")
                        appendLine("- Stage 1: VAD speech detection")
                        appendLine("- Stage 2: Speaker verification (green card)")
                        appendLine("- Stage 3: Cartesia WebSocket transcription")
                    } else {
                        appendLine("Recent logs (showing last ${logs.size} entries):")
                        appendLine()
                        logs.forEach { appendLine(it) }
                    }
                }
                
                logText.text = displayText
                
                // Auto-scroll to bottom
                scrollView.post {
                    scrollView.fullScroll(android.widget.ScrollView.FOCUS_DOWN)
                }
                
            } catch (e: Exception) {
                logText.text = "Error loading logs: ${e.message}"
            }
        }
    }
    

    

    
    private fun clearLogs() {
        lifecycleScope.launch {
            try {
                AppLogger.clearLogs()
                logText.text = "In-app logs cleared. Refresh to see new logs."
            } catch (e: Exception) {
                logText.text = "Error clearing logs: ${e.message}"
            }
        }
    }
}