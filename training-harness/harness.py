import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # Absolute path of the folder that contains this script
DATA = Path(os.environ.get('HARNESS_DATA', ROOT / 'data')).expanduser()
TRAIN_DIR = DATA / 'train'  # Images for training
HOLDOUT_DIR = (
    DATA / 'holdout'
)  # Images the model never trains on, used for the final accuracy check
OUT_DIR = DATA / 'out'  # build outputs
CHECKPOINT = OUT_DIR / 'classifier.pt'  # PyTorch weights
COREML_MODEL = OUT_DIR / 'Classifier.mlpackage'  # IOS
TFLITE_MODEL = OUT_DIR / 'Classifier.tflite'  # Android
LABELS = OUT_DIR / 'labels.txt'

INPUT_SIZE = 224
IMAGENET_MEAN = [
    0.485,
    0.456,
    0.406,
]  #  (R, G, B)
IMAGENET_STD = [
    0.229,
    0.224,
    0.225,
]  #  (R, G, B) standard deviation of ImageNet, used as the divisor
IMAGE_SUFFIXES = (
    '.jpg',
    '.jpeg',
    '.png',
)


def load_dataset_config(path=ROOT / 'dataset.json'):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def labelled_images(root: str | Path):
    for class_dir in sorted(Path(root).iterdir()):
        if not class_dir.is_dir():
            continue
        for path in sorted(class_dir.iterdir()):
            if path.suffix.lower() in IMAGE_SUFFIXES:
                yield class_dir.name, path


def device_input(path: str | Path):
    """
    Crop which both native modules will apply (exif orientation, center square and then bi-linear resize)
    """
    import numpy as np
    from PIL import Image, ImageOps

    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source).convert('RGB')
        image = ImageOps.fit(oriented, (INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 255.0
