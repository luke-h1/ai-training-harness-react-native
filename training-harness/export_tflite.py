"""Export the checkpoint as a TFLite classifier for Android.

  python3 export_tflite.py [checkpoint.pt] [Classifier.tflite] [labels.txt]

Runs in the Linux image from Dockerfile.tflite: LiteRT Torch has no macOS
build.
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from ai_edge_litert.interpreter import Interpreter

from harness import CHECKPOINT, INPUT_SIZE, LABELS, TFLITE_MODEL
from model import NhwcDeployable, load_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint', nargs='?', default=str(CHECKPOINT))
    parser.add_argument('output', nargs='?', default=str(TFLITE_MODEL))
    parser.add_argument('labels', nargs='?', default=str(LABELS))
    args = parser.parse_args()

    import litert_torch  # pyright: ignore[reportMissingImports]  # only installed in Dockerfile.tflite

    net, classes, _ = load_checkpoint(args.checkpoint)
    example = torch.rand(1, INPUT_SIZE, INPUT_SIZE, 3)
    with torch.no_grad():
        edge_model = litert_torch.convert(NhwcDeployable(net).eval(), (example,))
    edge_model.export(args.output)
    Path(args.labels).write_text('\n'.join(classes) + '\n', encoding='utf-8')

    interpreter = Interpreter(model_path=args.output)
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    expected = {
        'input shape': ([1, INPUT_SIZE, INPUT_SIZE, 3], np.asarray(input_detail['shape']).tolist()),
        'output shape': ([1, len(classes)], np.asarray(output_detail['shape']).tolist()),
        'input dtype': (np.float32, input_detail['dtype']),
        'output dtype': (np.float32, output_detail['dtype']),
    }

    for name, (want, got) in expected.items():
        if want != got:
            raise SystemExit(f'unexpected TFLite {name}: {got}, want {want}')
    print(f'saved {args.output} and {args.labels}: {len(classes)} classes')


if __name__ == '__main__':
    main()
