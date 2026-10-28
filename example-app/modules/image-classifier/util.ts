import { native } from './native';
import type { Classification, Prediction } from './types';

export function byConfidence(a: Prediction, b: Prediction): number {
  return b.confidence - a.confidence;
}

export function isAvailable(): boolean {
  return native !== null;
}

export async function classifyImage(imageUri: string): Promise<Classification> {
  if (!native) {
    throw new Error(
      'ImageClassifier is not in this build. Run a development build.',
    );
  }
  const result = await native.classifyAsync(imageUri);

  return {
    predictions: [...result.predictions].sort(byConfidence),
    labels: [...result.labels].sort(byConfidence),
  };
}

export async function getModelLabels(): Promise<string[]> {
  return native ? native.getLabelsAsync() : [];
}
