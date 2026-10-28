import { Classification, Prediction } from '@modules/image-classifier';

export interface Labels {
  labels: Record<string, string>;
  backgroundLabel: string | null;
  minConfidence: number;
}

export type Verdict =
  | {
      kind: 'match';
      label: string;
      name: string;
      confidence: number;
    }
  | {
      kind: 'unsure';
      best: Prediction | null;
    }
  | { kind: 'none' };

export function displayName(label: string, brand: Labels): string {
  const name = brand.labels[label];
  if (name) {
    return name;
  }

  const spaced = label.replace(/[_-]+/g, ' ').trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function verdict(result: Classification, brand: Labels): Verdict {
  const best = result.predictions[0];
  if (!best) {
    return { kind: 'none' };
  }

  if (best.label === brand.backgroundLabel) {
    return { kind: 'none' };
  }

  if (best.confidence < brand.minConfidence) {
    return { kind: 'unsure', best };
  }

  return {
    kind: 'match',
    label: best.label,
    name: displayName(best.label, brand),
    confidence: best.confidence,
  };
}
