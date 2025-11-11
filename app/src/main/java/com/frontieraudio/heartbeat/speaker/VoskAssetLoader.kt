package com.frontieraudio.heartbeat.speaker

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream

internal object VoskAssetLoader {

    fun prepareAssetDirectory(
        context: Context,
        assetName: String,
        versionDirectory: String
    ): File {
        val targetDir = File(context.filesDir, "vosk/$versionDirectory")
        if (!targetDir.exists() || targetDir.list()?.isEmpty() == true) {
            targetDir.deleteRecursively()
            targetDir.mkdirs()
            unpackAssetZip(context, assetName, targetDir)
        }
        return targetDir
    }

    fun resolveModelDirectory(root: File, markerFileName: String): File {
        val direct = File(root, markerFileName)
        if (direct.exists()) {
            return root
        }
        val children = root.listFiles() ?: return root
        children.forEach { child ->
            val candidate = File(child, markerFileName)
            if (candidate.exists()) {
                return child
            }
        }
        return root
    }

    private fun unpackAssetZip(context: Context, assetName: String, destination: File) {
        try {
            context.assets.open(assetName).use { inputStream ->
                ZipInputStream(inputStream).use { zipStream ->
                    var entry: ZipEntry? = zipStream.nextEntry
                    while (entry != null) {
                        val outFile = File(destination, entry.name)
                        if (entry.isDirectory) {
                            if (!outFile.exists()) {
                                outFile.mkdirs()
                            }
                        } else {
                            outFile.parentFile?.mkdirs()
                            FileOutputStream(outFile).use { fileOut ->
                                zipStream.copyTo(fileOut)
                            }
                        }
                        zipStream.closeEntry()
                        entry = zipStream.nextEntry
                    }
                }
            }
        } catch (ioe: IOException) {
            destination.deleteRecursively()
            throw ioe
        }
    }
}
