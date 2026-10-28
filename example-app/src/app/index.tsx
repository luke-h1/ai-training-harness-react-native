import { brand } from '@/theme/brand';
import { Button } from '@/components/Button';
import { Results } from '@/components/Results';
import { usePalette } from '@/theme/palette';
import {
  classifyImage,
  isAvailable,
  type Classification,
} from '@modules/image-classifier';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';
import { StyleSheet } from 'react-native-unistyles';

export type State =
  | { status: 'idle' }
  | { status: 'working'; uri: string }
  | { status: 'done'; uri: string; result: Classification; millis: number }
  | { status: 'failed'; uri: string | null; message: string };

export default function Index() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const palette = usePalette();

  const pick = useCallback(async (source: 'camera' | 'library') => {
    let uri: string | null = null;
    try {
      if (source === 'camera') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();

        if (!permission.granted) {
          setState({
            status: 'failed',
            uri: null,
            message: 'Camera access is off.',
          });
          return;
        }
      }

      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ['images'],
        quality: 0.9,
      };

      const picked =
        source === 'camera'
          ? await ImagePicker.launchCameraAsync(options)
          : await ImagePicker.launchImageLibraryAsync(options);

      uri = picked.assets?.[0]?.uri ?? null;

      if (picked.canceled || !uri) {
        return;
      }

      setState({ status: 'working', uri });
      const started = performance.now();
      const result = await classifyImage(uri);
      setState({
        status: 'done',
        uri,
        result,
        millis: performance.now() - started,
      });
    } catch (error) {
      setState({
        status: 'failed',
        uri,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, []);

  const preview = state.status === 'idle' ? null : state.uri;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title} accessibilityRole='header'>
          {brand.name}
        </Text>
        <Text style={styles.muted}>{brand.tagline}</Text>
      </View>
      <View style={styles.preview}>
        {preview ? (
          <Image
            source={{ uri: preview }}
            style={StyleSheet.absoluteFill}
            contentFit='cover'
          />
        ) : (
          <Text style={styles.muted}>No photo yet</Text>
        )}
        {state.status === 'working' ? (
          <View style={styles.scrim}>
            <ActivityIndicator color={palette.onAccent} />
          </View>
        ) : null}
      </View>
      <View style={styles.actions}>
        <Button label='Take photo' primary onPress={() => pick('camera')} />
        <Button label='Choose photo' onPress={() => pick('library')} />
      </View>
      {!isAvailable() ? (
        <Text style={styles.muted}>
          The native classifier is missing from this build. Run `bunx expo prebuild -p ios && bun run ios -d` or
          `bunx prebuild -p android && bun run android -d`; Expo Go does not include local modules.
        </Text>
      ) : null}

      {state.status === 'failed' ? (
        <Text style={styles.error}>{state.message}</Text>
      ) : null}

      {state.status === 'done' ? <Results state={state} /> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create((theme, rt) => ({
  root: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    paddingTop: rt.insets.top + 24,
    paddingBottom: rt.insets.bottom + 32,
    paddingHorizontal: 20,
    gap: 20,
  },
  header: {
    gap: 6,
  },
  title: {
    fontSize: 34,
    fontWeight: '700',
    color: theme.colors.text,
  },
  muted: {
    fontSize: 15,
    color: theme.colors.muted,
  },
  error: {
    fontSize: 15,
    color: '#C0392B',
  },
  preview: {
    aspectRatio: 1,
    borderRadius: 20,
    borderCurve: 'continuous',
    overflow: 'hidden',
    backgroundColor: theme.colors.track,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrim: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
}));
