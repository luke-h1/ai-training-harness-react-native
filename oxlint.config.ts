import { defineConfig } from 'oxlint';

export default defineConfig({
  plugins: ['typescript', 'react', 'import', 'promise', 'unicorn'],
  categories: {
    correctness: 'error',
    suspicious: 'warn',
  },
  env: {
    builtin: true,
  },
  settings: {
    react: {
      version: '19.3',
    },
  },
  ignorePatterns: [
    '**/node_modules/**',
    '**/build/**',
    '**/dist/**',
    '**/.expo/**',
    'example-app/android/**',
    'example-app/ios/**',
    'training-harness/**',
  ],
  rules: {
    'import/no-unassigned-import': ['warn', { allow: ['expo-router/entry', '**/unistyles'] }],
    // Hermes has no Array#toSorted or Array#toReversed, so these fixes crash at runtime
    'unicorn/no-array-sort': 'off',
    'unicorn/no-array-reverse': 'off',
    'no-nested-ternary': 'error',
    'no-var': 'error',
    'prefer-const': 'error',
    'typescript/ban-ts-comment': 'error',
    'typescript/no-explicit-any': 'error',
    'typescript/no-non-null-asserted-optional-chain': 'error',
    'typescript/no-require-imports': 'error',
    'typescript/prefer-as-const': 'error',
    'react/jsx-key': 'error',
    'react/react-in-jsx-scope': 'off',
    'import/no-cycle': 'error',
    'promise/no-return-wrap': 'error',
    'promise/no-new-statics': 'error',
  },
});
