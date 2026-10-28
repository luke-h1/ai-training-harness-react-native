"""Export the checkpoint.pt as a Core ML image classifier for iOS.

python3 export_coreml.py [checkpoint.pt] [Classifier.mlpackage]
"""

import argparse

import coremltools as ct
import torch

from harness import CHECKPOINT, COREML_MODEL, INPUT_SIZE
from model import Deployable, load_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint', nargs='?', default=str(CHECKPOINT))
    parser.add_argument('output', nargs='?', default=str(COREML_MODEL))
    parser.add_argument('--version', default='1.0')
    args = parser.parse_args()

    net, classes, checkpoint = load_checkpoint(args.checkpoint)
    example = torch.rand(1, 3, INPUT_SIZE, INPUT_SIZE)
    traced = torch.jit.trace(Deployable(net).eval(), example)
    model = ct.convert(
        traced,
        inputs=[ct.ImageType(name='image', shape=example.shape, scale=1 / 255.0)],
        classifier_config=ct.ClassifierConfig(classes),
        minimum_deployment_target=ct.target.iOS16,
    )
    assert isinstance(model, ct.models.MLModel)
    model.short_description = f'{checkpoint["arch"]} image classifier for {len(classes)} classes: {", ".join(classes)}'
    model.version = args.version
    model.save(args.output)
    print(f'saved {args.output}: {len(classes)} classes')


if __name__ == '__main__':
    main()
