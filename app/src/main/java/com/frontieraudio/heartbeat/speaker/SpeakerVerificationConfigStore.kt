package com.frontieraudio.heartbeat.speaker

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class SpeakerVerificationConfigStore(context: Context) {

    private val dataStore = context.speakerVerificationConfigDataStore

    val config: Flow<SpeakerVerificationConfig> = dataStore.data.map { prefs ->
        SpeakerVerificationConfig(
            matchThreshold = prefs[THRESHOLD_KEY] ?: SpeakerVerificationConfig.DEFAULT_MATCH_THRESHOLD,
            positiveRetentionMillis = prefs[POSITIVE_RETENTION_KEY] ?: SpeakerVerificationConfig.DEFAULT_POSITIVE_RETENTION_MS,
            negativeCooldownMillis = prefs[NEGATIVE_COOLDOWN_KEY] ?: SpeakerVerificationConfig.DEFAULT_NEGATIVE_COOLDOWN_MS
        )
    }

    suspend fun updateMatchThreshold(threshold: Float) {
        dataStore.edit { prefs ->
            prefs[THRESHOLD_KEY] = threshold.coerceIn(
                SpeakerVerificationConfig.MIN_THRESHOLD,
                SpeakerVerificationConfig.MAX_THRESHOLD
            )
        }
    }

    suspend fun updateTiming(positiveRetention: Long, negativeCooldown: Long) {
        dataStore.edit { prefs ->
            prefs[POSITIVE_RETENTION_KEY] = positiveRetention
            prefs[NEGATIVE_COOLDOWN_KEY] = negativeCooldown
        }
    }

    companion object {
        private val THRESHOLD_KEY = floatPreferencesKey("speaker_verification_threshold")
        private val POSITIVE_RETENTION_KEY = longPreferencesKey("speaker_verification_positive_retention_ms")
        private val NEGATIVE_COOLDOWN_KEY = longPreferencesKey("speaker_verification_negative_cooldown_ms")
    }
}
