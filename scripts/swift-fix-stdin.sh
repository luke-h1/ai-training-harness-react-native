#!/usr/bin/env bash
set -euo pipefail

#  scripts/swift-fix-stdin.sh <buffer-path> < Source.swift > Fixed.swift
#
# Swift formatter for Zed format on save: swiftformat, then swiftlint --fix.
# Zed formatters must read stdin and write stdout, and swiftlint --fix only
# edits files, so this script runs both tools on a temporary copy.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
name="$(basename "${1:-Buffer.swift}")"

dir="$(mktemp -d)"
trap 'rm -rf "$dir"' EXIT
file="$dir/$name"
cat >"$file"

# unusedArguments renames a parameter to _ when the body does not use it yet,
# which deletes names mid-edit. scripts/lint-swift.sh still applies it.
if command -v swiftformat >/dev/null 2>&1; then
  swiftformat --config "$ROOT/.swiftformat" --disable unusedArguments --quiet "$file" >&2
fi
if command -v swiftlint >/dev/null 2>&1; then
  swiftlint lint --fix --quiet --config "$ROOT/.swiftlint.yml" "$file" >&2
fi

cat "$file"
