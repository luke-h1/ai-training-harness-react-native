"""Download a single-label image classification dataset from Open Images V7.

  python3 download.py [--per-class N] [--workers 16] [--dry-run]

Reads the classes from dataset.json and writes
data/train/<label>/<image-id>.jpg and data/holdout/<label>/<image-id>.jpg,
plus data/manifest.jsonl with the licence and author of every file.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from harness import DATA, HOLDOUT_DIR, TRAIN_DIR, load_dataset_config

META_DIR = DATA / 'meta'
MANIFEST = DATA / 'manifest.jsonl'
BASE_URL = 'https://storage.googleapis.com/openimages'
CLASS_DESCRIPTIONS_URL = f'{BASE_URL}/v5/class-descriptions-boxable.csv'
HIERARCHY_URL = f'{BASE_URL}/2018_04/bbox_labels_600_hierarchy.json'
IMAGE_URL = 'https://s3.amazonaws.com/open-images-dataset/{split}/{image_id}.jpg'
UPRIGHT = ('', '0', '0.0')

Row = dict[str, str]


@dataclass
class Candidate:
    image_id: str
    split: str
    label: str
    path: Path
    license: str
    author: str
    author_url: str
    source_url: str
    title: str


@dataclass
class ImageEvidence:
    labels: set[str] = field(default_factory=set)
    largest_box: dict[str, float] = field(default_factory=dict)
    ambiguous: bool = False
    depiction: bool = False


# Open Images metadata


def fetch(url: str) -> Path:
    path = META_DIR / url.rsplit('/', 1)[1]
    if not path.exists():
        META_DIR.mkdir(parents=True, exist_ok=True)
        print(f'fetching {url}', flush=True)
        partial = path.with_suffix(path.suffix + '.part')
        urllib.request.urlretrieve(url, partial)
        partial.rename(path)
    return path


def read_csv(path: Path) -> Iterator[Row]:
    with open(path, encoding='utf-8', newline='') as handle:
        yield from csv.DictReader(handle)


def split_files(split: str) -> dict[str, Path]:
    return {
        'boxes': fetch(f'{BASE_URL}/v5/{split}-annotations-bbox.csv'),
        'labels': fetch(f'{BASE_URL}/v5/{split}-annotations-human-imagelabels-boxable.csv'),
        'images': fetch(f'{BASE_URL}/2018_04/{split}/{split}-images-with-rotation.csv'),
    }


# Map our labels to Open Images MIDs
def class_mids(classes: dict[str, str]) -> dict[str, str]:
    """
    Return the Open Images MID for each label. `classes` maps a label to an
    Open Images class name, for example {"cat": "Cat"}.
    """
    with open(fetch(CLASS_DESCRIPTIONS_URL), encoding='utf-8', newline='') as handle:
        mid_by_name = {row[1].casefold(): row[0] for row in csv.reader(handle) if len(row) == 2}

    missing = [name for name in classes.values() if name.casefold() not in mid_by_name]
    if missing:
        raise SystemExit(f'not an open images boxable class: {", ".join(missing)}')

    return {label: mid_by_name[name.casefold()] for label, name in classes.items()}


def walk(node, ancestors: list[str], visit) -> None:
    visit(node['LabelName'], ancestors)
    for child in node.get('Subcategory', []):
        walk(child, [*ancestors, node['LabelName']], visit)


def expand_classes(hierarchy, mid_by_label: dict[str, str]) -> tuple[dict[str, str], set[str]]:
    """
    Map every MID under a target class to that class, and collect the MIDs
    that are ambiguous for the background class: the targets, their
    descendants, and their ancestors. For example, "Animal" can be a cat.
    """
    label_by_target = {mid: label for label, mid in mid_by_label.items()}
    label_by_mid: dict[str, str] = {}
    ambiguous: set[str] = set()

    def visit(mid: str, ancestors: list[str]) -> None:
        owners = {label_by_target[m] for m in [*ancestors, mid] if m in label_by_target}
        if len(owners) > 1:
            raise SystemExit(f'{mid} sits under more than one class: {sorted(owners)}')

        if owners:
            label_by_mid[mid] = owners.pop()
            ambiguous.add(mid)

        if mid in label_by_target:
            ambiguous.update(ancestors)

    walk(hierarchy, [], visit)

    for label, mid in mid_by_label.items():
        label_by_mid.setdefault(mid, label)
        ambiguous.add(mid)
    return label_by_mid, ambiguous


def box_area(row: Row) -> float:
    return (float(row['XMax']) - float(row['XMin'])) * (float(row['YMax']) - float(row['YMin']))


def collect_evidence(
    box_rows: Iterable[Row],
    label_rows: Iterable[Row],
    label_by_mid: dict[str, str],
    ambiguous: set[str],
) -> dict[str, ImageEvidence]:
    images: dict[str, ImageEvidence] = {}

    def record(row: Row) -> tuple[ImageEvidence, str | None]:
        evidence = images.setdefault(row['ImageID'], ImageEvidence())
        mid = row['LabelName']
        if mid in ambiguous:
            evidence.ambiguous = True

        label = label_by_mid.get(mid)
        if label is not None:
            evidence.labels.add(label)
        return evidence, label

    for row in box_rows:
        evidence, label = record(row)
        if label is not None:
            evidence.depiction |= row['IsDepiction'] == '1'
            evidence.largest_box[label] = max(evidence.largest_box.get(label, 0.0), box_area(row))

    for row in label_rows:
        if row['Confidence'] == '1':
            _ = record(row)

    return images


def assign_label(
    evidence: ImageEvidence, min_box_area: float, background: str | None
) -> str | None:
    """
    Return one label for the image, or None to skip it.
    """
    if evidence.depiction:
        return None

    if not evidence.labels:
        return background if background and not evidence.ambiguous else None

    if len(evidence.labels) > 1:
        return None

    (label,) = evidence.labels
    return label if evidence.largest_box.get(label, 0.0) >= min_box_area else None


def stable_hash(salt: str, image_id: str) -> int:
    return int(hashlib.sha1(f'{salt}:{image_id}'.encode()).hexdigest(), 16)


def is_holdout(image_id: str, percent: int) -> bool:
    return stable_hash('holdout', image_id) % 100 < percent


def find_candidates(
    split: str,
    config,
    label_by_mid: dict[str, str],
    ambiguous: set[str],
    background: str | None,
) -> Iterator[Candidate]:
    files = split_files(split)
    evidence = collect_evidence(
        read_csv(files['boxes']), read_csv(files['labels']), label_by_mid, ambiguous
    )

    for row in read_csv(files['images']):
        image_id = row['ImageID']
        if image_id not in evidence or row['Rotation'] not in UPRIGHT:
            continue

        label = assign_label(evidence[image_id], config['minBoxArea'], background)
        if label is None:
            continue

        target = HOLDOUT_DIR if is_holdout(image_id, config['holdoutPercent']) else TRAIN_DIR
        yield Candidate(
            image_id=image_id,
            split=split,
            label=label,
            path=target / label / f'{image_id}.jpg',
            license=row['License'],
            author=row['Author'],
            author_url=row['AuthorProfileURL'],
            source_url=row['OriginalLandingURL'],
            title=row['Title'],
        )


def save_image(payload: bytes, path: Path, max_side: int) -> None:
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(payload)) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix('.part')
    image.save(partial, 'JPEG', quality=90)
    partial.rename(path)


def download_one(candidate: Candidate, max_side: int) -> Candidate | None:
    if candidate.path.exists():
        return candidate

    url = IMAGE_URL.format(split=candidate.split, image_id=candidate.image_id)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            save_image(response.read(), candidate.path, max_side)
    except Exception as error:
        print(f'skip {candidate.image_id}: {error}', file=sys.stderr, flush=True)
        return None

    return candidate


def download_label(
    pool: ThreadPoolExecutor, candidates: list[Candidate], per_class: int, max_side: int
) -> list[Candidate]:
    """
    Download candidates in order until `per_class` images succeed or no
    candidates are left. Each batch only asks for the images that are still
    missing, so failed downloads are replaced from the rest of the list.
    """
    kept: list[Candidate] = []
    start = 0
    while len(kept) < per_class and start < len(candidates):
        batch = candidates[start : start + per_class - len(kept)]
        start += len(batch)
        results = pool.map(lambda c: download_one(c, max_side), batch)
        kept.extend(c for c in results if c is not None)
    return kept


def write_manifest(entries: list[Candidate]) -> None:
    with open(MANIFEST, 'w', encoding='utf-8') as handle:
        for entry in entries:
            record = {**asdict(entry), 'path': str(entry.path.relative_to(DATA))}
            _ = handle.write(json.dumps(record, ensure_ascii=False) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument('--per-class', type=int)
    _ = parser.add_argument('--workers', type=int, default=16)
    _ = parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    config = load_dataset_config()
    per_class: int = args.per_class or config['perClass']
    background: str | None = config.get('background')
    labels = [*config['classes'], *([background] if background else [])]

    mid_by_label = class_mids(config['classes'])
    with open(fetch(HIERARCHY_URL), encoding='utf-8') as handle:
        label_by_mid, ambiguous = expand_classes(json.load(handle), mid_by_label)

    candidates: dict[str, list[Candidate]] = {label: [] for label in labels}
    for split in config['splits']:
        for candidate in find_candidates(split, config, label_by_mid, ambiguous, background):
            candidates[candidate.label].append(candidate)

    for label in labels:
        candidates[label].sort(key=lambda c: stable_hash('order', c.image_id))
        print(f'{label:<12} {len(candidates[label]):>6} candidates', flush=True)

    if args.dry_run:
        return

    manifest: list[Candidate] = []
    with ThreadPoolExecutor(args.workers) as pool:
        for label in labels:
            kept = download_label(pool, candidates[label], per_class, config['maxSide'])
            if len(kept) < per_class:
                print(f'{label}: only {len(kept)} of {per_class} available', flush=True)
            print(f'{label:<12} {len(kept):>6} images', flush=True)
            manifest.extend(kept)

    write_manifest(manifest)
    print(f'wrote {MANIFEST}: {len(manifest)} images')


if __name__ == '__main__':
    main()
