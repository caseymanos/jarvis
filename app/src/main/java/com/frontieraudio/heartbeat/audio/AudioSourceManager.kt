package com.frontieraudio.heartbeat.audio

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.MediaRecorder
import android.util.Log
import androidx.core.content.ContextCompat

enum class AudioSourceType {
    DEVICE_MICROPHONE,
    BLUETOOTH_MICROPHONE,
    WIRED_HEADSET
}

data class AudioSourceInfo(
    val type: AudioSourceType,
    val displayName: String,
    val isAvailable: Boolean,
    val audioSource: Int
)

class AudioSourceManager(private val context: Context) {
    
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    private val bluetoothAdapter = bluetoothManager?.adapter
    
    private var currentSource = AudioSourceType.DEVICE_MICROPHONE
    
    fun getCurrentAudioSource(): AudioSourceInfo {
        return when (currentSource) {
            AudioSourceType.DEVICE_MICROPHONE -> AudioSourceInfo(
                type = AudioSourceType.DEVICE_MICROPHONE,
                displayName = "Device Microphone",
                isAvailable = true,
                audioSource = MediaRecorder.AudioSource.MIC
            )
            AudioSourceType.BLUETOOTH_MICROPHONE -> AudioSourceInfo(
                type = AudioSourceType.BLUETOOTH_MICROPHONE,
                displayName = "Bluetooth Microphone",
                isAvailable = isBluetoothMicrophoneAvailable(),
                audioSource = MediaRecorder.AudioSource.MIC // Will use startBluetoothSco() for routing
            )
            AudioSourceType.WIRED_HEADSET -> AudioSourceInfo(
                type = AudioSourceType.WIRED_HEADSET,
                displayName = "Wired Headset",
                isAvailable = isWiredHeadsetAvailable(),
                audioSource = MediaRecorder.AudioSource.MIC
            )
        }
    }
    
    fun getAvailableSources(): List<AudioSourceInfo> {
        val sources = mutableListOf<AudioSourceInfo>()
        
        // Device microphone is always available
        sources.add(AudioSourceInfo(
            type = AudioSourceType.DEVICE_MICROPHONE,
            displayName = "Device Microphone",
            isAvailable = true,
            audioSource = MediaRecorder.AudioSource.MIC
        ))
        
        // Check Bluetooth microphone availability
        if (isBluetoothMicrophoneAvailable()) {
            sources.add(AudioSourceInfo(
                type = AudioSourceType.BLUETOOTH_MICROPHONE,
                displayName = "Bluetooth Microphone",
                isAvailable = true,
                audioSource = MediaRecorder.AudioSource.MIC
            ))
        }
        
        // Check wired headset availability
        if (isWiredHeadsetAvailable()) {
            sources.add(AudioSourceInfo(
                type = AudioSourceType.WIRED_HEADSET,
                displayName = "Wired Headset",
                isAvailable = true,
                audioSource = MediaRecorder.AudioSource.MIC
            ))
        }
        
        return sources
    }
    
    fun switchToSource(sourceType: AudioSourceType): Boolean {
        val sourceInfo = getAvailableSources().find { it.type == sourceType }
        if (sourceInfo == null || !sourceInfo.isAvailable) {
            Log.w(TAG, "Audio source $sourceType is not available")
            return false
        }
        
        Log.i(TAG, "Switching audio source from $currentSource to $sourceType")
        
        when (sourceType) {
            AudioSourceType.BLUETOOTH_MICROPHONE -> {
                return enableBluetoothSco()
            }
            AudioSourceType.DEVICE_MICROPHONE -> {
                disableBluetoothSco()
                return true
            }
            AudioSourceType.WIRED_HEADSET -> {
                // Wired headset uses default routing, no special handling needed
                return true
            }
        }
    }
    
    private fun isBluetoothMicrophoneAvailable(): Boolean {
        // Check Bluetooth permission
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH) != PackageManager.PERMISSION_GRANTED) {
            return false
        }
        
        // Check if Bluetooth is enabled
        if (bluetoothAdapter?.isEnabled != true) {
            return false
        }
        
        // Check if headset profile is connected
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bluetoothManager?.adapter
        
        if (adapter == null || !adapter.isEnabled) {
            return false
        }
        
        // Check for connected Bluetooth devices
        return adapter.getProfileProxy(context, object : BluetoothProfile.ServiceListener {
            override fun onServiceConnected(profile: Int, proxy: BluetoothProfile?) {
                // This is async, not useful for immediate check
            }
            
            override fun onServiceDisconnected(profile: Int) {
                // This is async, not useful for immediate check
            }
        }, BluetoothProfile.HEADSET) != null
    }
    
    private fun isWiredHeadsetAvailable(): Boolean {
        return audioManager.isWiredHeadsetOn
    }
    
    private fun enableBluetoothSco(): Boolean {
        // Check Bluetooth Sco permission
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.MODIFY_AUDIO_SETTINGS) != PackageManager.PERMISSION_GRANTED) {
            Log.w(TAG, "MODIFY_AUDIO_SETTINGS permission not granted")
            return false
        }
        
        return try {
            if (audioManager.isBluetoothScoAvailableOffCall) {
                audioManager.startBluetoothSco()
                audioManager.setBluetoothScoOn(true)
                currentSource = AudioSourceType.BLUETOOTH_MICROPHONE
                Log.i(TAG, "Bluetooth SCO enabled successfully")
                true
            } else {
                Log.w(TAG, "Bluetooth SCO is not available on this device")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to enable Bluetooth SCO", e)
            false
        }
    }
    
    private fun disableBluetoothSco() {
        try {
            audioManager.setBluetoothScoOn(false)
            audioManager.stopBluetoothSco()
            currentSource = AudioSourceType.DEVICE_MICROPHONE
            Log.i(TAG, "Bluetooth SCO disabled")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to disable Bluetooth SCO", e)
        }
    }
    
    fun updateCurrentSourceFromSystemState() {
        if (audioManager.isBluetoothScoOn && isBluetoothMicrophoneAvailable()) {
            currentSource = AudioSourceType.BLUETOOTH_MICROPHONE
        } else if (audioManager.isWiredHeadsetOn) {
            currentSource = AudioSourceType.WIRED_HEADSET
        } else {
            currentSource = AudioSourceType.DEVICE_MICROPHONE
        }
        
        Log.d(TAG, "Updated current source to: $currentSource")
    }
    
    companion object {
        private const val TAG = "AudioSourceManager"
    }
}
