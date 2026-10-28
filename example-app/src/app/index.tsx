import { Classification } from '@modules/image-classifier';
import { StyleSheet, Text, View } from 'react-native';

type State =
  | { status: 'idle' }
  | { status: 'working'; uri: string }
  | { status: 'done'; uri: string; result: Classification; millis: number }
  | { status: 'failed'; uri: string | null; message: string };

const percent = (value: number) => `${Math.round(value * 100)}%`;

export default function Index() {
  return (
    <View style={styles.container}>
      <Text>Edit src/app/index.tsx to edit this screen.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
