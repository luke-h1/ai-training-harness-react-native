export interface Palette {
  background: string;
  surface: string;
  text: string;
  muted: string;
  accent: string;
  onAccent: string;
  track: string;
}

export interface Brand {
  name: string;
  slug: string;
  scheme: string;
  iosBundleIdentifier: string;
  androidPackage: string;
  tagline: string;
  cameraPermission: string;
  photosPermission: string;
  colors: {
    light: Palette;
    dark: Palette;
  };
  labels: Record<string, string>;
  backgroundLabel: string | null;
  minConfidence: number;
}

export const brand: Brand = {
  name: 'Lens',
  slug: 'lens',
  scheme: 'lens',
  iosBundleIdentifier: 'com.example.lens',
  androidPackage: 'com.example.lens',
  tagline: 'Point the camera at something to see what it is.',
  cameraPermission: 'The camera takes a photo for the on-device classifier.',
  photosPermission:
    'A photo from your library goes to the on-device classifier.',
  colors: {
    light: {
      background: '#F6F5F1',
      surface: '#FFFFFF',
      text: '#1B1B19',
      muted: '#6B6A64',
      accent: '#2F6B4F',
      onAccent: '#FFFFFF',
      track: '#E7E5DE',
    },
    dark: {
      background: '#121211',
      surface: '#1E1E1C',
      text: '#F2F1EC',
      muted: '#A3A29B',
      accent: '#7FC4A0',
      onAccent: '#0D1F16',
      track: '#2C2C29',
    },
  },
  labels: {
    bicycle: 'Bicycle',
    bird: 'Bird',
    car: 'Car',
    cat: 'Cat',
    dog: 'Dog',
    flower: 'Flower',
    other: 'Something else',
  },
  backgroundLabel: 'other',
  minConfidence: 0.5,
};
