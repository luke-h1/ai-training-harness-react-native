package expo.modules.imageclassifier

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel

private const val INPUT_SIZE = 224
private const val MODEL_ASSET = "Classifier.tflite"
private const val LABELS_ASSET = "labels.txt"

object Classifier {
  private var interpreter: Interpreter? = null
  private var labels: List<String> = emptyList()

  @Synchronized
  fun labels(context: Context): List<String> {
    load(context)
    return labels
  }

  @Synchronized
  fun classify(context: Context, uri: Uri, limit: Int = 5): List<Map<String, Any>> {
    val model = load(context)
    val input = toInputBuffer(decodeBitmap(context, uri))
    val probabilities = Array(1) { FloatArray(labels.size) }
    model.run(input, probabilities)

    return labels.indices
      .sortedByDescending { probabilities[0][it] }
      .take(limit)
      .map { index ->
        mapOf(
          "label" to labels[index],
          "confidence" to probabilities[0][index].toDouble(),
        )
      }
  }

  private fun load(context: Context): Interpreter {
    interpreter?.let { return it }

    labels = context.assets.open(LABELS_ASSET).bufferedReader().use { reader ->
      reader.readLines().map { it.trim() }.filter { it.isNotEmpty() }
    }

    if (labels.isEmpty()) {
      throw IllegalStateException("$LABELS_ASSET is empty")
    }
    val model = context.assets.openFd(MODEL_ASSET).use { asset ->
      FileInputStream(asset.fileDescriptor).use { stream ->
        val buffer = stream.channel.map(
          FileChannel.MapMode.READ_ONLY,
          asset.startOffset,
          asset.declaredLength,
        )
        Interpreter(buffer, Interpreter.Options().setNumThreads(4))
      }
    }
    if (!model.getInputTensor(0).shape().contentEquals(intArrayOf(1, INPUT_SIZE, INPUT_SIZE, 3))) {
      throw IllegalStateException("$MODEL_ASSET does not take a [1,$INPUT_SIZE,$INPUT_SIZE,3] input")
    }

    if (model.getOutputTensor(0).shape()[1] != labels.size) {
      throw IllegalStateException("$LABELS_ASSET does not match the outputs of $MODEL_ASSET")
    }

    interpreter = model
    return model
  }

  private fun decodeBitmap(context: Context, uri: Uri): Bitmap {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    val stream = context.contentResolver.openInputStream(uri)
      ?: throw IllegalArgumentException("Could not read image")

    stream.use { BitmapFactory.decodeStream(it, null, bounds) }

    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
      throw IllegalArgumentException("Could not read image dimensions")
    }

    var sampleSize = 1
    while (
      bounds.outWidth / (sampleSize * 2) >= INPUT_SIZE * 2 &&
      bounds.outHeight / (sampleSize * 2) >= INPUT_SIZE * 2
    ) {
      sampleSize *= 2
    }
    val options = BitmapFactory.Options().apply {
      inSampleSize = sampleSize
      inPreferredConfig = Bitmap.Config.ARGB_8888
    }

    val bitmap = context.contentResolver.openInputStream(uri)?.use { stream ->
      BitmapFactory.decodeStream(stream, null, options)
    } ?: throw IllegalArgumentException("Could not decode image")

    val orientation = context.contentResolver.openInputStream(uri)?.use { stream ->
      ExifInterface(stream).getAttributeInt(
        ExifInterface.TAG_ORIENTATION,
        ExifInterface.ORIENTATION_NORMAL,
      )
    } ?: ExifInterface.ORIENTATION_NORMAL

    val matrix = Matrix().apply {
      when (orientation) {
        ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> setScale(-1f, 1f)

        ExifInterface.ORIENTATION_ROTATE_180 -> setRotate(180f)

        ExifInterface.ORIENTATION_FLIP_VERTICAL -> {
          setRotate(180f)
          postScale(-1f, 1f)
        }

        ExifInterface.ORIENTATION_TRANSPOSE -> {
          setRotate(90f)
          postScale(-1f, 1f)
        }

        ExifInterface.ORIENTATION_ROTATE_90 -> setRotate(90f)

        ExifInterface.ORIENTATION_TRANSVERSE -> {
          setRotate(-90f)
          postScale(-1f, 1f)
        }

        ExifInterface.ORIENTATION_ROTATE_270 -> setRotate(-90f)
      }
    }
    if (matrix.isIdentity) {
      return bitmap
    }
    return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
      .also { rotated ->
        if (rotated != bitmap) {
          bitmap.recycle()
        }
      }
  }

  private fun toInputBuffer(bitmap: Bitmap): ByteBuffer {
    val side = minOf(bitmap.width, bitmap.height)
    val cropped = Bitmap.createBitmap(
      bitmap,
      (bitmap.width - side) / 2,
      (bitmap.height - side) / 2,
      side,
      side,
    )
    if (cropped != bitmap) {
      bitmap.recycle()
    }
    val scaled = Bitmap.createScaledBitmap(cropped, INPUT_SIZE, INPUT_SIZE, true)
    if (scaled != cropped) {
      cropped.recycle()
    }

    val pixels = IntArray(INPUT_SIZE * INPUT_SIZE)
    scaled.getPixels(pixels, 0, INPUT_SIZE, 0, 0, INPUT_SIZE, INPUT_SIZE)
    scaled.recycle()
    val input = ByteBuffer.allocateDirect(INPUT_SIZE * INPUT_SIZE * 3 * 4)
      .order(ByteOrder.nativeOrder())
    for (pixel in pixels) {
      input.putFloat(((pixel shr 16) and 0xff) / 255f)
      input.putFloat(((pixel shr 8) and 0xff) / 255f)
      input.putFloat((pixel and 0xff) / 255f)
    }
    input.rewind()
    return input
  }
}
