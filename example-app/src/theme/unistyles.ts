import { StyleSheet } from 'react-native-unistyles';

import { brand } from './brand';

const appThemes = {
  light: { colors: brand.colors.light },
  dark: { colors: brand.colors.dark },
};

type AppThemes = typeof appThemes;

declare module 'react-native-unistyles' {
  export interface UnistylesThemes extends AppThemes {}
}

StyleSheet.configure({
  themes: appThemes,
  settings: {
    adaptiveThemes: true,
  },
});
