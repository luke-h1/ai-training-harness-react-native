#!/usr/bin/env bash
set -euo pipefail

#  ./scripts/lint-swift.sh [file ...]
#  LINT_CHECK=1 ./scripts/lint-swift.sh

cd "$(dirname "$0")/.."

if ! command -v swiftlint >/dev/null 2>&1; then
  echo "swiftlint not found - skipping Swift lint. Install with: brew install swiftlint" >&2
  exit 0
fi

format() {
  if ! command -v swiftformat >/dev/null 2>&1; then
    echo "swiftformat not found - skipping format. Install with: brew install swiftformat" >&2
    return 0
  fi
  if [ "${LINT_CHECK:-}" = "1" ]; then
    swiftformat --lint "$@"
  else
    swiftformat "$@"
  fi
}

files=("$@")
status=0
if [ "${#files[@]}" -eq 0 ]; then
  format example-app/modules || status=1
  [ "${LINT_CHECK:-}" = "1" ] || swiftlint lint --fix --quiet || true
  swiftlint lint --strict --quiet || status=1
else
  format "${files[@]}" || status=1
  [ "${LINT_CHECK:-}" = "1" ] || swiftlint lint --fix --quiet -- "${files[@]}" || true
  swiftlint lint --strict --quiet -- "${files[@]}" || status=1
fi
exit "$status"
