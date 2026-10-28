import json
import sys
from pathlib import Path
from typing import Any

import pytest
import torch
from PIL import Image

import evaluate
import model

CLASSES = ['cat', 'dog', 'other']
COLOURS = {'cat': 'orange', 'dog': 'brown', 'other': 'blue', 'zebra': 'white'}


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    _ = torch.manual_seed(0)
    net = model.build_model('mobilenet_v3_small', len(CLASSES))
    path = tmp_path / 'classifier.pt'
    torch.save({'arch': 'mobilenet_v3_small', 'classes': CLASSES, 'state_dict': net.state_dict()}, path)
    return path


@pytest.fixture
def holdout(tmp_path: Path) -> Path:
    """
    Two images for each class, in sizes that are not square, plus a class
    that the checkpoint does not know.
    """
    root = tmp_path / 'holdout'
    for label, colour in COLOURS.items():
        (root / label).mkdir(parents=True)
        Image.new('RGB', (320, 240), colour).save(root / label / 'a.jpg')
        Image.new('RGB', (200, 400), colour).save(root / label / 'b.png')
    return root


@pytest.fixture
def run_eval(monkeypatch: pytest.MonkeyPatch, checkpoint: Path, holdout: Path, tmp_path: Path):
    out_dir = tmp_path / 'out'
    monkeypatch.setattr(evaluate, 'load_checkpoint', lambda: model.load_checkpoint(checkpoint))
    monkeypatch.setattr(evaluate, 'OUT_DIR', out_dir)

    def run(*args: str) -> dict[str, Any]:
        monkeypatch.setattr(sys, 'argv', ['evaluate.py', *args, '--holdout', str(holdout)])
        evaluate.main()
        return json.loads((out_dir / f'eval-{args[0]}.json').read_text())

    return run
