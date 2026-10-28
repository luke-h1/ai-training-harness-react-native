import sys
from pathlib import Path

import numpy as np
import pytest

import evaluate
import model
from harness import INPUT_SIZE

from .conftest import CLASSES


def result(label: str, top1: bool, top3: bool) -> dict[str, str | bool]:
    return {'label': label, 'top1': top1, 'top3': top3}


def test_summarise_scores_overall_and_per_class():
    report = evaluate.summarise(
        [
            result('cat', True, True),
            result('cat', False, True),
            result('dog', False, False),
            result('dog', True, True),
        ],
        CLASSES,
    )

    assert report['n'] == 4
    assert report['top1'] == 0.5
    assert report['top3'] == 0.75
    assert report['per_class'] == {
        'cat': {'n': 2, 'top1': 0.5},
        'dog': {'n': 2, 'top1': 0.5},
    }


def test_summarise_leaves_out_classes_without_images():
    report = evaluate.summarise([result('cat', True, True)], CLASSES)

    assert list(report['per_class']) == ['cat']


def test_torch_backend_returns_one_probability_per_class(checkpoint: Path):
    net, classes, _ = model.load_checkpoint(checkpoint)
    predict = evaluate.torch_backend(model.Deployable(net).eval())

    probabilities = predict(np.full((INPUT_SIZE, INPUT_SIZE, 3), 0.5, dtype=np.float32))

    assert probabilities.shape == (len(classes),)
    assert probabilities.sum() == pytest.approx(1.0, abs=1e-5)
    assert (probabilities >= 0).all()


def test_torch_eval_scores_known_classes_and_skips_the_rest(run_eval):
    report = run_eval('torch')

    assert report['n'] == 6
    assert set(report['per_class']) == set(CLASSES)
    assert 0.0 <= report['top1'] <= report['top3'] <= 1.0
    assert 'parity' not in report


def test_eval_fails_when_top1_is_below_the_minimum(run_eval):
    with pytest.raises(SystemExit, match='FAIL: top1'):
        run_eval('torch', '--min-top1', '1.01')


def test_backend_identical_to_torch_has_full_parity(run_eval, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(evaluate, 'coreml_backend', lambda _path, _classes: torch_reference())

    report = run_eval('coreml', '--max-disagreement', '0')

    assert report['parity'] == {'disagreement': 0.0, 'max_probability_delta': 0.0}


def test_backend_that_disagrees_with_torch_fails(run_eval, monkeypatch: pytest.MonkeyPatch):
    def reversed_reference(_path, _classes):
        reference = torch_reference()
        return lambda pixels: reference(pixels)[::-1].copy()

    monkeypatch.setattr(evaluate, 'coreml_backend', reversed_reference)

    with pytest.raises(SystemExit, match='FAIL: disagrees with torch'):
        run_eval('coreml')


def test_tflite_backend_rejects_labels_that_do_not_match(tmp_path: Path):
    labels = tmp_path / 'labels.txt'
    labels.write_text('dog\ncat\nother\n', encoding='utf-8')

    with pytest.raises(SystemExit, match='does not match the checkpoint classes'):
        evaluate.tflite_backend(str(tmp_path / 'missing.tflite'), str(labels), CLASSES)


@pytest.mark.skipif(sys.platform != 'darwin', reason='Core ML runs only on macOS')
def test_exported_coreml_model_matches_torch(run_eval, checkpoint: Path, tmp_path: Path, monkeypatch):
    import export_coreml

    package = tmp_path / 'Classifier.mlpackage'
    monkeypatch.setattr(sys, 'argv', ['export_coreml.py', str(checkpoint), str(package)])
    export_coreml.main()

    report = run_eval('coreml', '--model', str(package), '--max-disagreement', '1')

    assert report['n'] == 6
    assert report['parity']['max_probability_delta'] < 0.01


def torch_reference():
    net, _, _ = evaluate.load_checkpoint()
    return evaluate.torch_backend(model.Deployable(net).eval())
