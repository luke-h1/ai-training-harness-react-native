"""Score an exported model on data/holdout and compare it with PyTorch.

python3 evaluate.py torch
python3 evaluate.py coreml [--model Classifier.mlpackage]     # macOS
python3 evaluate.py tflite [--model Classifier.tflite]        # Docker image
"""

import argparse
import json
import sys
from typing import NotRequired, TypedDict

import numpy as np
import torch

from harness import COREML_MODEL, HOLDOUT_DIR, LABELS, OUT_DIR, TFLITE_MODEL, labelled_images
from harness import device_input as load_pixels
from model import Deployable, load_checkpoint


def torch_backend(wrapped):
    def predict(pixels):
        with torch.no_grad():
            batch = torch.from_numpy(pixels).permute(2, 0, 1).unsqueeze(0)
            return wrapped(batch)[0].numpy()

    return predict


def coreml_backend(path, classes):
    import coremltools as cml
    from PIL import Image

    model = cml.models.MLModel(path)

    def predict(pixels):
        image = Image.fromarray((pixels * 255).round().astype(np.uint8))
        probabilities = model.predict({'image': image})['classLabel_probs']
        return np.array([probabilities[name] for name in classes], dtype=np.float32)

    return predict


def tflite_backend(path, labels_path, classes):
    from ai_edge_litert.interpreter import Interpreter

    with open(labels_path, encoding='utf-8') as handle:
        labels = [line.strip() for line in handle if line.strip()]
    if labels != classes:
        raise SystemExit(f'{labels_path} does not match the checkpoint classes')

    interpreter = Interpreter(model_path=path, num_threads=4)
    interpreter.allocate_tensors()
    input_index = interpreter.get_input_details()[0]['index']
    output_index = interpreter.get_output_details()[0]['index']

    def predict(pixels):
        interpreter.set_tensor(input_index, pixels[np.newaxis])
        interpreter.invoke()
        return interpreter.get_tensor(output_index)[0]

    return predict


class ClassScore(TypedDict):
    n: int
    top1: float


class Parity(TypedDict):
    disagreement: float
    max_probability_delta: float


class Report(TypedDict):
    n: int
    top1: float
    top3: float
    per_class: dict[str, ClassScore]
    parity: NotRequired[Parity]


def summarise(results, classes) -> Report:
    per_class: dict[str, ClassScore] = {}
    for name in classes:
        rows = [r for r in results if r['label'] == name]
        if rows:
            per_class[name] = {
                'n': len(rows),
                'top1': sum(r['top1'] for r in rows) / len(rows),
            }

    total = len(results)
    return {
        'n': total,
        'top1': sum(r['top1'] for r in results) / total,
        'top3': sum(r['top3'] for r in results) / total,
        'per_class': per_class,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('backend', choices=['torch', 'coreml', 'tflite'])
    parser.add_argument('--model')
    parser.add_argument('--labels', default=str(LABELS))
    parser.add_argument('--holdout', default=str(HOLDOUT_DIR))
    parser.add_argument('--min-top1', type=float, default=0.0)
    parser.add_argument('--max-disagreement', type=float, default=0.01)
    args = parser.parse_args()

    net, classes, _ = load_checkpoint()
    reference = torch_backend(Deployable(net).eval())

    if args.backend == 'torch':
        predict = reference
    elif args.backend == 'coreml':
        predict = coreml_backend(args.model or str(COREML_MODEL), classes)
    else:
        predict = tflite_backend(args.model or str(TFLITE_MODEL), args.labels, classes)

    results = []
    disagreements = 0
    max_delta = 0.0

    for label, path in labelled_images(args.holdout):
        if label not in classes:
            continue

        pixels = load_pixels(path)
        probabilities = predict(pixels)
        ranked = [classes[i] for i in np.argsort(probabilities)[::-1][:3]]
        results.append({'label': label, 'top1': ranked[0] == label, 'top3': label in ranked})

        if args.backend != 'torch':
            expected = reference(pixels)
            disagreements += int(expected.argmax() != probabilities.argmax())
            max_delta = max(max_delta, float(np.abs(expected - probabilities).max()))

    if not results:
        raise SystemExit(f'no labelled images under {args.holdout}')

    report = summarise(results, classes)

    if args.backend != 'torch':
        report['parity'] = {
            'disagreement': disagreements / len(results),
            'max_probability_delta': max_delta,
        }

    for name, entry in report['per_class'].items():
        print(f'{name:<14} {entry["n"]:>5}  top1 {entry["top1"]:.3f}')

    print(f'\n{args.backend}: n {report["n"]}  top1 {report["top1"]:.3f}  top3 {report["top3"]:.3f}')

    if 'parity' in report:
        parity = report['parity']
        print(
            f'parity with torch: disagreement {parity["disagreement"]:.4f}  '
            f'max probability delta {parity["max_probability_delta"]:.6f}'
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f'eval-{args.backend}.json').write_text(json.dumps(report, indent=2) + '\n')

    failures = []
    if report['top1'] < args.min_top1:
        failures.append(f'top1 {report["top1"]:.3f} is below {args.min_top1}')

    if 'parity' in report and report['parity']['disagreement'] > args.max_disagreement:
        failures.append(f'disagrees with torch on {report["parity"]["disagreement"]:.2%} of photos')

    if failures:
        sys.exit('FAIL: ' + '; '.join(failures))


if __name__ == '__main__':
    main()
