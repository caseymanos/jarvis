package com.frontieraudio.heartbeat.speaker

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.vosk.SpeakerModel
import java.io.File

class SpeakerModelProvider(private val context: Context) {

    private val applicationContext = context.applicationContext
    private val modelLock = Any()
    @Volatile
    private var cachedModel: SpeakerModel? = null

    suspend fun getModel(): SpeakerModel = withContext(Dispatchers.IO) {
        cachedModel ?: synchronized(modelLock) {
            cachedModel ?: loadModel().also { cachedModel = it }
        }
    }

    fun clearCachedModel() {
        synchronized(modelLock) {
            cachedModel?.close()
            cachedModel = null
        }
    }

    private fun loadModel(): SpeakerModel {
        val targetDir = VoskAssetLoader.prepareAssetDirectory(
            context = applicationContext,
            assetName = MODEL_ASSET,
            versionDirectory = "model-spk-$MODEL_VERSION"
        )
        val modelDir = VoskAssetLoader.resolveModelDirectory(targetDir, MODEL_FILE_NAME)
        Log.i(TAG, "Loaded Vosk speaker model from ${modelDir.absolutePath}")
        return SpeakerModel(modelDir.absolutePath)
    }

    companion object {
        private const val TAG = "SpeakerModelProvider"
        private const val MODEL_ASSET = "vosk-model-spk.zip"
        private const val MODEL_VERSION = "0.4"
        private const val MODEL_FILE_NAME = "spk_model.bin"
    }
}
