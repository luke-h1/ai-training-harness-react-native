package expo.modules.imageclassifier

import android.net.Uri
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.label.ImageLabeling
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions
import expo.modules.kotlin.Promise
import expo.modules.kotlin.exception.CodedException
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.util.concurrent.Executors

private class ClassifyException(message: String, cause: Throwable? = null) : CodedException("ERR_CLASSIFY", message, cause)

private val classifyExecutor = Executors.newSingleThreadExecutor()

class ImageClassifierModule : Module() {
  private val context
    get() = appContext.reactContext ?: throw ClassifyException("no application context?")

  override fun definition() = ModuleDefinition {
    Name("ImageClassifier")


    AsyncFunction("getLabelsAsync") {
      Classifier.labels(context)
    }

    AsyncFunction("classifyAsync") { imageUri: String, promise: Promise ->
      val context = context

      classifyExecutor.execute {
        try {
          val uri = Uri.parse(imageUri)
          val predictions = Classifier.classify(context, uri)
          val labeler = ImageLabeling.getClient(ImageLabelerOptions.DEFAULT_OPTIONS)
          labeler.process(InputImage.fromFilePath(context, uri))
            .addOnSuccessListener(classifyExecutor) { labels ->
              labeler.close()
              promise.resolve(
                mapOf(
                  "predictions" to predictions,
                  "labels" to labels.take(10).map {
                    mapOf("label" to it.text, "confidence" to it.confidence.toDouble())
                  },
                )
              )
            }
            .addOnFailureListener(classifyExecutor) { error ->
              labeler.close()
              promise.reject(ClassifyException(error.message ?: "ML kit labelling failed", error))
            }

        } catch (error: Exception) {
          promise.reject(ClassifyException(error.message ?: "Could not classify image", error))
        }
      }
    }

    Function("hello") {
      "Hello world! 👋"
    }
  }
}
