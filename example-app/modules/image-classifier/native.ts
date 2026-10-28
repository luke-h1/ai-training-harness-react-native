import { requireOptionalNativeModule } from 'expo';

import type { ImageClassifierModule } from './types';

export const native =
  requireOptionalNativeModule<ImageClassifierModule>('ImageClassifier');
