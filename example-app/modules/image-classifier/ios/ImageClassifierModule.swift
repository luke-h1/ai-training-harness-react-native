import ExpoModulesCore

public class ImageClassifierModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ImageClassifier")

    Function("hello") {
      return "Hello world! 👋"
    }
  }
}
