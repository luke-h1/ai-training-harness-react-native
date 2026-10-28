#!/usr/bin/env bash
# Export the trained checkpoint for both platforms and copy it into the app's native module.
#   scripts/build-model.sh            # export, evaluate, install
#   MIN_TOP1=0.9 scripts/build-model.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TRAINING="$ROOT/training-harness"
DATA="${HARNESS_DATA:-$TRAINING/data}"
MODULE="$ROOT/example-app/modules/image-classifier"
IMAGE="${TFLITE_IMAGE:-classifier-tflite}"
MIN_TOP1="${MIN_TOP1:-0.85}"
VERSION="${MODEL_VERSION:-1.0}"

if [[ ! -f "$DATA/out/classifier.pt" ]]; then
  echo "No checkpoint at $DATA/out/classifier.pt. Run training-harness/train.py first." >&2
  exit 1
fi

cd "$TRAINING"
export HARNESS_DATA="$DATA"

echo "== Core ML"
uv run python export_coreml.py --version "$VERSION"
uv run python evaluate.py coreml --min-top1 "$MIN_TOP1"

echo "== TFLite"
docker build --platform linux/amd64 -f Dockerfile.tflite -t "$IMAGE" . >/dev/null
in_docker() {
  docker run --rm --platform linux/amd64 \
    -v "$TRAINING:/work" -v "$DATA:/data" -e HARNESS_DATA=/data \
    "$IMAGE" python3 "$@"
}
in_docker export_tflite.py
in_docker evaluate.py tflite --min-top1 "$MIN_TOP1"

echo "== Install"
rm -rf "$MODULE/ios/Classifier.mlmodelc"
xcrun coremlcompiler compile "$DATA/out/Classifier.mlpackage" "$MODULE/ios/" >/dev/null
mkdir -p "$MODULE/android/src/main/assets"
cp "$DATA/out/Classifier.tflite" "$DATA/out/labels.txt" "$MODULE/android/src/main/assets/"
cp "$DATA/out/eval-coreml.json" "$DATA/out/eval-tflite.json" "$MODULE/"
echo "Installed model $VERSION into $MODULE"
