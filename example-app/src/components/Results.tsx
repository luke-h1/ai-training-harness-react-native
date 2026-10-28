import type { State } from '@/app';
import { brand } from '@/theme/brand';
import { displayName, verdict, type Verdict } from '@/lib/ai';
import { percent } from '@/util/percent';
import { Text, View } from 'react-native';
import { StyleSheet } from 'react-native-unistyles';

function headlineFor(answer: Verdict): string {
  switch (answer.kind) {
    case 'match':
      return `${answer.name} · ${percent(answer.confidence)}`;
    case 'unsure':
      return 'Not sure';
    default:
      return 'Nothing the model knows';
  }
}

interface ResultsProps {
  state: Extract<State, { status: 'done' }>;
}

export function Results({ state }: ResultsProps) {
  const answer = verdict(state.result, brand);
  const headline = headlineFor(answer);

  return (
    <View style={styles.container}>
      <View style={styles.card} accessibilityLabel={headline}>
        <Text style={styles.headline}>{headline}</Text>
        <Text style={styles.muted}>
          On device in {Math.round(state.millis)} ms
        </Text>
      </View>
      <View style={styles.list}>
        <Text style={styles.section}>Custom model</Text>
        {state.result.predictions.map(prediction => (
          <View
            key={prediction.label}
            style={styles.prediction}
            accessible
            accessibilityLabel={`${displayName(prediction.label, brand)} ${percent(prediction.confidence)}`}
          >
            <View style={styles.row}>
              <Text style={styles.text}>
                {displayName(prediction.label, brand)}
              </Text>
              <Text style={[styles.muted, styles.number]}>
                {percent(prediction.confidence)}
              </Text>
            </View>
            <View style={styles.track}>
              <View style={styles.bar(prediction.confidence)} />
            </View>
          </View>
        ))}
      </View>
      {state.result.labels.length > 0 ? (
        <View style={styles.labels}>
          <Text style={styles.section}>General labels</Text>
          <View style={styles.chips}>
            {state.result.labels.map(label => (
              <Text key={label.label} style={styles.chip}>
                {label.label} {percent(label.confidence)}
              </Text>
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create(theme => ({
  container: {
    gap: 20,
  },
  text: {
    fontSize: 16,
    color: theme.colors.text,
  },
  muted: {
    fontSize: 15,
    color: theme.colors.muted,
  },
  number: {
    fontVariant: ['tabular-nums'],
  },
  section: {
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
    color: theme.colors.muted,
  },
  headline: {
    fontSize: 24,
    fontWeight: '700',
    color: theme.colors.text,
  },
  card: {
    gap: 4,
    padding: 16,
    borderRadius: 16,
    borderCurve: 'continuous',
    backgroundColor: theme.colors.surface,
  },
  list: {
    gap: 12,
  },
  prediction: {
    gap: 6,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  track: {
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.track,
    overflow: 'hidden',
  },
  bar: (confidence: number) => ({
    width: `${Math.max(2, confidence * 100)}%`,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.accent,
  }),
  labels: {
    gap: 10,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    fontSize: 14,
    color: theme.colors.text,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    overflow: 'hidden',
    backgroundColor: theme.colors.surface,
  },
}));
