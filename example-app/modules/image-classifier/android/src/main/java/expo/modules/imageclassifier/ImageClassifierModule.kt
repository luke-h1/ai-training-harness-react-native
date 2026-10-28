package expo.modules.imageclassifier

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class ImageClassifierModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("ImageClassifier")

    Function("hello") {
      "Hello world! 👋"
    }
  }
}
