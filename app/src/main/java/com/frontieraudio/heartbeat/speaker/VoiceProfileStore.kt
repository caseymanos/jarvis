package com.frontieraudio.heartbeat.speaker

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map

class VoiceProfileStore(context: Context) {

    private val dataStore = context.voiceProfileDataStore

    val voiceProfileFlow: Flow<VoiceProfile?> = dataStore.data.map { prefs ->
        val embeddingString = prefs[stringPreferencesKey(VoiceProfile.KEY_EMBEDDING)] ?: return@map null
        val snapshot = mapOf(
            VoiceProfile.KEY_ID to (prefs[stringPreferencesKey(VoiceProfile.KEY_ID)] ?: ""),
            VoiceProfile.KEY_EMBEDDING to embeddingString,
            VoiceProfile.KEY_SAMPLE_RATE to (prefs[stringPreferencesKey(VoiceProfile.KEY_SAMPLE_RATE)] ?: return@map null),
            VoiceProfile.KEY_FRAME_SIZE to (prefs[stringPreferencesKey(VoiceProfile.KEY_FRAME_SIZE)] ?: return@map null),
            VoiceProfile.KEY_UPDATED_AT to (prefs[stringPreferencesKey(VoiceProfile.KEY_UPDATED_AT)] ?: return@map null),
            VoiceProfile.KEY_SAMPLE_COUNT to (prefs[stringPreferencesKey(VoiceProfile.KEY_SAMPLE_COUNT)] ?: "0")
        )
        VoiceProfile.fromPreferences(snapshot)
    }

    suspend fun getVoiceProfile(): VoiceProfile? = voiceProfileFlow.firstOrNull()

    suspend fun saveVoiceProfile(profile: VoiceProfile) {
        dataStore.edit { prefs ->
            clearExisting(prefs)
            profile.toPreferenceMap().forEach { (key, value) ->
                prefs[stringPreferencesKey(key)] = value
            }
        }
    }

    suspend fun clearVoiceProfile() {
        dataStore.edit { prefs ->
            clearExisting(prefs)
        }
    }

    private fun clearExisting(prefs: androidx.datastore.preferences.core.MutablePreferences) {
        listOf(
            VoiceProfile.KEY_ID,
            VoiceProfile.KEY_EMBEDDING,
            VoiceProfile.KEY_SAMPLE_RATE,
            VoiceProfile.KEY_FRAME_SIZE,
            VoiceProfile.KEY_UPDATED_AT,
            VoiceProfile.KEY_SAMPLE_COUNT
        ).forEach { keyName ->
            prefs.remove(stringPreferencesKey(keyName))
        }
    }
}
