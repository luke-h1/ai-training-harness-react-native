#!/usr/bin/env bash
set -euo pipefail

#  ./scripts/kotlin-lsp.sh
#  KOTLIN_LSP_HOME=/path/to/kotlin-lsp ./scripts/kotlin-lsp.sh
#
# Generates android/ and writes workspace.json at the repo root, so kotlin-lsp
# in Zed can resolve ExpoModulesCore and the other Gradle modules. Run it again
# after you add a native dependency or change a build.gradle.

APP="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$APP/.." && pwd)"
KOTLIN_LSP_HOME="${KOTLIN_LSP_HOME:-$HOME/.local/share/kotlin-lsp}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"

for script in export_workspace.py enrich_workspace.py; do
  if [[ ! -f "$KOTLIN_LSP_HOME/$script" ]]; then
    echo "$KOTLIN_LSP_HOME/$script not found. Set KOTLIN_LSP_HOME." >&2
    exit 1
  fi
done

cd "$APP"
CI=1 bunx expo prebuild -p android --no-install

# kotlin-lsp imports the Gradle project, then writes workspace.json. The enrich
# step adds source roots for modules under node_modules and attaches -sources.jar
# files, so go to definition opens source instead of class stubs.
python3 "$KOTLIN_LSP_HOME/export_workspace.py" "$APP/android" "$ROOT"
python3 "$KOTLIN_LSP_HOME/enrich_workspace.py" "$ROOT"

echo "Wrote $ROOT/workspace.json. In Zed, run 'editor: restart language server'."
