export interface Prediction {
  label: string;
  confidence: number;
}

export interface Classification {
  /**
   * The custom model trained in ../training
   */
  predictions: Prediction[];
  /**
   * The platform's labeler: ML Kit on Android, Vision on iOS.
   */
  labels: Prediction[];
}

export interface ImageClassifierModule {
  classifyAsync: (imageUri: string) => Promise<Classification>;
  getLabelsAsync: () => Promise<string[]>;
}
