package com.frontieraudio.heartbeat.speaker

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.vosk.Model

class SpeechModelProvider(context: Context) {

    private val applicationContext = context.applicationContext
    private val modelLock = Any()
    @Volatile
    private var cachedModel: Model? = null

    suspend fun getModel(): Model = withContext(Dispatchers.IO) {
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

    private fun loadModel(): Model {
        val targetDir = VoskAssetLoader.prepareAssetDirectory(
            context = applicationContext,
            assetName = MODEL_ASSET,
            versionDirectory = "model-small-$MODEL_VERSION"
        )
        val modelDir = VoskAssetLoader.resolveModelDirectory(targetDir, MODEL_MARKER_FILE)
        Log.i(TAG, "Loaded Vosk base model from ${modelDir.absolutePath}")
        return Model(modelDir.absolutePath)
    }

    companion object {
        private const val TAG = "SpeechModelProvider"
        private const val MODEL_ASSET = "vosk-model-small-en-us-0.15.zip"
        private const val MODEL_VERSION = "en-us-0.15"
        private const val MODEL_MARKER_FILE = "am/final.mdl"
    }
}
