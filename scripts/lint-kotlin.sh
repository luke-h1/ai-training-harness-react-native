#!/usr/bin/env bash
set -euo pipefail

#  ./scripts/lint-kotlin.sh [file ...]
#  LINT_CHECK=1 ./scripts/lint-kotlin.sh (check only no fix)

cd "$(dirname "$0")/.."

if ! command -v ktlint >/dev/null 2>&1; then
  echo "ktlint not found - skipping Kotlin lint. Install with: brew install ktlint" >&2
  exit 0
fi

files=("$@")
if [ "${#files[@]}" -eq 0 ]; then
  while IFS= read -r file; do
    files+=("$file")
  done < <(find app/modules -type d \( -name build -o -name node_modules \) -prune -o -type f \( -name '*.kt' -o -name '*.kts' \) -print)
  if [ "${#files[@]}" -eq 0 ]; then
    echo "No Kotlin files to lint."
    exit 0
  fi
fi

if [ "${LINT_CHECK:-}" = "1" ]; then
  ktlint --relative -- "${files[@]}"
else
  ktlint --format --relative -- "${files[@]}"
fi
