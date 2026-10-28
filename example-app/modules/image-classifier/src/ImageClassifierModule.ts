import { NativeModule, requireNativeModule } from 'expo';

declare class ImageClassifierModule extends NativeModule<{}> {
  hello(): string;
}

export default requireNativeModule<ImageClassifierModule>('ImageClassifier');
