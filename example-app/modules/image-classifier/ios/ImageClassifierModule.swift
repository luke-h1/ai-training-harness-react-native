import CoreML
import ExpoModulesCore
import ImageIO
import Vision

private let classifierModel: Result<MLModel, Error> = Result {
  guard
    let bundleUrl = Bundle(for: ImageClassifierModule.self)
    .url(forResource: "ImageClassifierModel", withExtension: "bundle"),
    let modelUrl = Bundle(url: bundleUrl)?
    .url(forResource: "Classifier", withExtension: "mlmodelc")
  else {
    throw ModelMissingException()
  }
  let configuration = MLModelConfiguration()
  #if targetEnvironment(simulator)
    configuration.computeUnits = .cpuOnly
  #endif
  return try MLModel(contentsOf: modelUrl, configuration: configuration)
}

private final class ModelMissingException: Exception, @unchecked Sendable {
  override var reason: String {
    "Classifier.mlmodelc is not in the ImageClassifierModel bundle. Run scripts/build-model.sh."
  }
}

private final class ImageReadException: Exception, @unchecked Sendable {
  override var reason: String {
    "Could not read the image"
  }
}

/// decode with EXIF orientation applied
private func orientedImage(at url: URL) throws -> CGImage {
  let options: [CFString: Any] = [
    kCGImageSourceCreateThumbnailFromImageAlways: true,
    kCGImageSourceCreateThumbnailWithTransform: true,
    kCGImageSourceThumbnailMaxPixelSize: 1024
  ]

  guard
    let source = CGImageSourceCreateWithURL(url as CFURL, nil),
    let image = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary)
  else {
    throw ImageReadException()
  }

  return image
}

private func classify(_ image: CGImage, limit: Int) throws -> [[String: Any]] {
  let model = try classifierModel.get()

  guard
    let input = model.modelDescription.inputDescriptionsByName.values.first,
    let constraint = input.imageConstraint,
    let outputName = model.modelDescription.predictedProbabilitiesName
  else {
    throw ModelMissingException()
  }

  let pixels = try MLFeatureValue(
    cgImage: image,
    constraint: constraint,
    options: [.cropAndScale: VNImageCropAndScaleOption.centerCrop.rawValue]
  )

  let features = try MLDictionaryFeatureProvider(dictionary: [input.name: pixels])
  let output = try model.prediction(from: features)
  let probabilities = output.featureValue(for: outputName)?.dictionaryValue ?? [:]

  return
    probabilities.compactMap { key, value in (key as? String).map { (label: $0, confidence: value.doubleValue) } }
      .sorted { $0.confidence > $1.confidence }
      .prefix(limit)
      .map { ["label": $0.label, "confidence": $0.confidence] }
}

private func encode(_ observations: [VNClassificationObservation], limit: Int) -> [[String: Any]] {
  observations.prefix(limit).map {
    ["label": $0.identifier, "confidence": Double($0.confidence)]
  }
}

/// The simulator has no Neural Engine. Vision fails there with "Failed to
/// create espresso context" unless the request runs on the CPU.
private func runOnCpuInSimulator(_ requests: [VNRequest]) {
  #if targetEnvironment(simulator)
    if #available(iOS 17.0, *) {
      let cpu = MLComputeDevice.allComputeDevices.first {
        if case .cpu = $0 { return true }
        return false
      }
      guard let cpu else { return }
      for request in requests {
        guard let stages = try? request.supportedComputeStageDevices else { continue }
        for stage in stages.keys {
          request.setComputeDevice(cpu, for: stage)
        }
      }
    } else {
      requests.forEach { $0.usesCPUOnly = true }
    }
  #endif
}

public class ImageClassifierModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ImageClassifier")

    AsyncFunction("getLabelsAsync") { () -> [String] in
      try classifierModel.get().modelDescription.classLabels as? [String] ?? []
    }

    AsyncFunction("classifyAsync") { (imageUri: URL, promise: Promise) in
      DispatchQueue.global(qos: .userInitiated).async {
        do {
          let predictions = try classify(orientedImage(at: imageUri), limit: 5)
          let general = VNClassifyImageRequest()
          runOnCpuInSimulator([general])

          try? VNImageRequestHandler(url: imageUri).perform([general])
          let labels = (general.results ?? []).filter { $0.confidence > 0.1 }
          promise.resolve([
            "predictions": predictions,
            "labels": encode(labels, limit: 10)
          ])
        } catch {
          promise.reject(error)
        }
      }
    }
  }
}
