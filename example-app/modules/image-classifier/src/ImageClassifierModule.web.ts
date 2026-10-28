import { registerWebModule, NativeModule } from 'expo';

// ImageClassifierModule is not available on the web platform.
class ImageClassifierModule extends NativeModule<{}> {}

export default registerWebModule(ImageClassifierModule, 'ImageClassifierModule');
