import type { Palette } from '@/theme/brand';
import { useUnistyles } from 'react-native-unistyles';

export type { Palette } from '@/theme/brand';

export function usePalette(): Palette {
  return useUnistyles().theme.colors;
}
