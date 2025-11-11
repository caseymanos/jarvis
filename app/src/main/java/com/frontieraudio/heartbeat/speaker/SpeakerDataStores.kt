package com.frontieraudio.heartbeat.speaker

import android.content.Context
import androidx.datastore.preferences.preferencesDataStore

internal val Context.voiceProfileDataStore by preferencesDataStore(name = "voice_profile")
internal val Context.speakerVerificationConfigDataStore by preferencesDataStore(name = "speaker_verification_config")
