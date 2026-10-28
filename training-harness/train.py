"""Fine-tune a MobileNetV3 classifier

  python3 train.py [--arch mobilenet_v3_small] [--epochs 10]

Writes data/out/classifier.pt: the weights, the ordered class list and the architecture.
"""

import argparse
import os
import random
import time

import torch
import torch.nn as nn
from harness import CHECKPOINT, IMAGENET_MEAN, IMAGENET_STD, INPUT_SIZE, TRAIN_DIR
from model import ARCHITECTURES, build_model
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler
from torchvision import datasets, transforms

SEED = 22


def stratified_split(samples, fraction, seed):
    by_class = {}
    for index, (_, label) in enumerate(samples):
        by_class.setdefault(label, []).append(index)

    train, val = [], []
    rng = random.Random(seed)

    for _, indices in sorted(by_class.items()):
        rng.shuffle(indices)
        cut = max(1, int(fraction * len(indices)))
        val.extend(indices[:cut])
        train.extend(indices[cut:])
    return train, val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch', choices=sorted(ARCHITECTURES), default='mobilenet_v3_small')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch', type=int, default=64)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--workers', type=int, default=min(6, os.cpu_count() or 1))
    parser.add_argument('--device')
    parser.add_argument('--data', default=str(TRAIN_DIR))
    parser.add_argument('--out', default=str(CHECKPOINT))
    args = parser.parse_args()

    torch.manual_seed(SEED)

    device = torch.device(
        args.device or ('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
    )

    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(INPUT_SIZE, scale=(0.5, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )

    val_tf = transforms.Compose(
        [
            transforms.Resize(INPUT_SIZE),
            transforms.CenterCrop(INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )

    base = datasets.ImageFolder(args.data)
    classes = base.classes

    print(f'{len(base)} images, {len(classes)} classes: {classes} on {device}', flush=True)

    train_idx, val_idx = stratified_split(base.samples, 0.12, SEED)
    train_ds = Subset(datasets.ImageFolder(args.data, transform=train_tf), train_idx)
    val_ds = Subset(datasets.ImageFolder(args.data, transform=val_tf), val_idx)

    counts = [0] * len(classes)

    for index in train_idx:
        counts[base.samples[index][1]] += 1

    weights = [1.0 / counts[base.samples[index][1]] for index in train_idx]
    sampler = WeightedRandomSampler(weights, num_samples=len(train_idx), replacement=True)
    train_dl = DataLoader(
        train_ds,
        batch_size=args.batch,
        sampler=sampler,
        num_workers=args.workers,
        persistent_workers=args.workers > 0,
    )
    val_dl = DataLoader(val_ds, batch_size=args.batch, num_workers=min(args.workers, 4))

    model = build_model(args.arch, len(classes), pretrained=True).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)

    def evaluate(per_class=False):
        model.eval()
        hits = [0] * len(classes)
        seen = [0] * len(classes)
        with torch.no_grad():
            for x, y in val_dl:
                predicted = model(x.to(device)).argmax(1).cpu()
                for label, guess in zip(y.tolist(), predicted.tolist(), strict=True):
                    seen[label] += 1
                    hits[label] += int(label == guess)

        if per_class:
            print('per-class validation accuracy:', flush=True)
            for index, name in enumerate(classes):
                accuracy = hits[index] / seen[index] if seen[index] else 0.0
                print(f'  {name:<14} {accuracy:.2f}  ({hits[index]}/{seen[index]})', flush=True)
        return sum(hits) / sum(seen)

    best, best_state = -1.0, None

    for epoch in range(args.epochs):
        model.train()
        started = time.time()
        hits = total = 0
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            out = model(x)
            loss_fn(out, y).backward()
            opt.step()
            hits += (out.argmax(1) == y).sum().item()
            total += y.numel()

        sched.step()
        val_acc = evaluate()
        print(
            f'epoch {epoch + 1}/{args.epochs}: train acc {hits / total:.3f} '
            f'val acc {val_acc:.3f} ({time.time() - started:.0f}s)',
            flush=True,
        )
        if val_acc > best:
            best = val_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    evaluate(per_class=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save(
        {
            'arch': args.arch,
            'classes': classes,
            'state_dict': model.cpu().state_dict(),
            'val_accuracy': best,
        },
        args.out,
    )
    print(f'best validation accuracy {best:.3f}; saved {args.out}', flush=True)


if __name__ == '__main__':
    main()
