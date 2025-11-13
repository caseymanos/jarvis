package com.frontieraudio.heartbeat.transcription

import android.content.Context
import android.util.Log
import com.frontieraudio.heartbeat.debug.AppLogger
import com.frontieraudio.heartbeat.location.LocationData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

/**
 * Manages saving and storing transcriptions with GPS location data
 */
class TranscriptionManager(private val context: Context) {
    
    private val transcriptionDir = File(context.filesDir, "transcriptions")
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.getDefault())
    private val jsonDateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.getDefault())
    
    init {
        if (!transcriptionDir.exists()) {
            transcriptionDir.mkdirs()
        }
        Log.d(TAG, "TranscriptionManager initialized, storage dir: ${transcriptionDir.absolutePath}")
    }
    
    suspend fun saveTranscription(
        transcript: String,
        confidence: Float?,
        locationData: LocationData?,
        timestamp: Long = System.currentTimeMillis(),
        isVerified: Boolean = false,
        verificationSimilarity: Float? = null
    ) = withContext(Dispatchers.IO) {
        try {
            val transcriptionRecord = TranscriptionRecord(
                id = UUID.randomUUID().toString(),
                transcript = transcript,
                confidence = confidence,
                locationData = locationData,
                timestamp = timestamp,
                isVerified = isVerified,
                verificationSimilarity = verificationSimilarity
            )
            
            // Save as JSON
            val filename = "transcript_${dateFormat.format(Date(timestamp))}_${transcriptionRecord.id}.json"
            val file = File(transcriptionDir, filename)
            file.writeText(transcriptionRecord.toJson())
            
            // Append to daily log file
            appendToDailyLog(transcriptionRecord)
            
            AppLogger.i(TAG, "💾 Saved transcription: '${transcript.take(50)}${if (transcript.length > 50) "..." else ""}' with GPS: ${locationData != null}")
            
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to save transcription", e)
        }
    }
    
    suspend fun getAllTranscriptions(): List<TranscriptionRecord> = withContext(Dispatchers.IO) {
        try {
            val files = transcriptionDir.listFiles { _, name -> 
                name.startsWith("transcript_") && name.endsWith(".json") 
            }?.sortedByDescending { it.lastModified() } ?: emptyList()
            
            files.mapNotNull { file ->
                try {
                    TranscriptionRecord.fromJson(file.readText())
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse transcription file: ${file.name}", e)
                    null
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load transcriptions", e)
            emptyList()
        }
    }
    
    suspend fun exportTranscriptions(): String = withContext(Dispatchers.IO) {
        buildString {
            appendLine("Transcription Export - Generated: ${jsonDateFormat.format(Date())}")
            appendLine("Format: ID | Timestamp | Transcript | Confidence | GPS Location | Verified")
            appendLine("=".repeat(120))
            
            getAllTranscriptions().forEach { record ->
                val timestamp = jsonDateFormat.format(Date(record.timestamp))
                val gps = record.locationData?.let { 
                    "${it.latitude},${it.longitude}${it.accuracy?.let { acc -> " (±${acc}m)" } ?: ""}"
                } ?: "No GPS"
                val verified = if (record.isVerified) "✅ (${record.verificationSimilarity?.let { "%.3f".format(it) } ?: ""})" else "❌"
                val confidence = record.confidence?.let { "%.2f".format(it) } ?: "N/A"
                
                appendLine("${record.id} | $timestamp | ${record.transcript} | $confidence | $gps | $verified")
                appendLine()
            }
        }
    }
    
    private suspend fun appendToDailyLog(record: TranscriptionRecord) = withContext(Dispatchers.IO) {
        try {
            val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date(record.timestamp))
            val logFile = File(transcriptionDir, "daily_log_$today.txt")
            
            val logEntry = buildString {
                append(jsonDateFormat.format(Date(record.timestamp)))
                append(" | GPS: ")
                append(record.locationData?.let { 
                    "${it.latitude},${it.longitude}${it.accuracy?.let { acc -> " (±${acc}m)" } ?: ""}"
                } ?: "No GPS")
                append(" | Verified: ${if (record.isVerified) "✅" else "❌"}")
                append(" | Confidence: ${record.confidence?.let { "%.2f".format(it) } ?: "N/A"}")
                append(" | Transcript: ${record.transcript}")
                appendLine()
            }
            
            logFile.appendText(logEntry)
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to append to daily log", e)
        }
    }
    
    data class TranscriptionRecord(
        val id: String,
        val transcript: String,
        val confidence: Float?,
        val locationData: LocationData?,
        val timestamp: Long,
        val isVerified: Boolean,
        val verificationSimilarity: Float?
    ) {
        fun toJson(): String {
            val json = JSONObject().apply {
                put("id", id)
                put("transcript", transcript)
                put("confidence", confidence)
                put("timestamp", timestamp)
                put("isVerified", isVerified)
                put("verificationSimilarity", verificationSimilarity)
                
                locationData?.let { location ->
                    put("location", JSONObject().apply {
                        put("latitude", location.latitude)
                        put("longitude", location.longitude)
                        location.accuracy?.let { put("accuracy", it) }
                        put("timestamp", location.timestampMillis)
                    })
                }
            }
            return json.toString(2)
        }
        
        companion object {
            fun fromJson(jsonString: String): TranscriptionRecord {
                val json = JSONObject(jsonString)
                val locationJson = json.optJSONObject("location")
                val locationData = if (locationJson != null) {
                    LocationData(
                        latitude = locationJson.getDouble("latitude"),
                        longitude = locationJson.getDouble("longitude"),
                        accuracy = if (locationJson.has("accuracy")) locationJson.getDouble("accuracy").toFloat() else null,
                        timestampMillis = locationJson.getLong("timestamp")
                    )
                } else null
                
                return TranscriptionRecord(
                    id = json.getString("id"),
                    transcript = json.getString("transcript"),
                    confidence = if (json.has("confidence") && !json.isNull("confidence")) json.getDouble("confidence").toFloat() else null,
                    locationData = locationData,
                    timestamp = json.getLong("timestamp"),
                    isVerified = json.getBoolean("isVerified"),
                    verificationSimilarity = if (json.has("verificationSimilarity") && !json.isNull("verificationSimilarity")) json.getDouble("verificationSimilarity").toFloat() else null
                )
            }
        }
    }
    
    companion object {
        private const val TAG = "TranscriptionManager"
    }
}
