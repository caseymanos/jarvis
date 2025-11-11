package com.frontieraudio.heartbeat

import android.app.Application
import com.frontieraudio.heartbeat.speaker.SpeakerVerificationConfigStore
import com.frontieraudio.heartbeat.speaker.VoiceProfileStore

class HeartbeatApplication : Application() {
    
    val voiceProfileStore by lazy { VoiceProfileStore(applicationContext) }
    val configStore by lazy { SpeakerVerificationConfigStore(applicationContext) }
    
    companion object {
        private var instance: HeartbeatApplication? = null
        
        fun getInstance(): HeartbeatApplication {
            return instance ?: throw IllegalStateException("Application not initialized")
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        instance = this
    }
}

