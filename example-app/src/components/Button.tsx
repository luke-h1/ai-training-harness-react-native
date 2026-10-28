import { Pressable, type PressableStateCallbackType, Text } from 'react-native';
import { StyleSheet } from 'react-native-unistyles';

interface ButtonProps {
  label: string;
  primary?: boolean;
  onPress: () => void;
}

export function Button({ label, primary = false, onPress }: ButtonProps) {
  styles.useVariants({ primary });

  return (
    <Pressable
      accessibilityRole='button'
      onPress={onPress}
      style={styles.button}
    >
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create(theme => ({
  button: (state: PressableStateCallbackType) => ({
    flex: 1,
    minHeight: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderColor: theme.colors.muted,
    opacity: state.pressed ? 0.75 : 1,
    variants: {
      primary: {
        true: {
          backgroundColor: theme.colors.accent,
          borderWidth: 0,
        },
        false: {
          backgroundColor: theme.colors.surface,
          borderWidth: StyleSheet.hairlineWidth,
        },
      },
    },
  }),
  label: {
    fontSize: 16,
    fontWeight: '600',
    variants: {
      primary: {
        true: {
          color: theme.colors.onAccent,
        },
        false: {
          color: theme.colors.text,
        },
      },
    },
  },
}));
