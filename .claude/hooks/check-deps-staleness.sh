#!/bin/bash
# PreToolUse hook for Read/Grep.
# Warns if ~/ai/crypto_base_scanner_desktop/deps/ API docs are stale
# by comparing git hashes recorded in the docs against current HEADs
# of the dependency repos (resolved from local.config).

INPUT=$(cat)
# Read uses file_path, Grep uses path
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

DEPS_DIR="$HOME/ai/crypto_base_scanner_desktop/deps"

# Only check reads of files inside this deps dir
case "$FILE_PATH" in
  "$DEPS_DIR"/*) ;;
  *) exit 0 ;;
esac

LOCAL_CONFIG="$HOME/ai/crypto_base_scanner_desktop/local.config"
if [ ! -f "$LOCAL_CONFIG" ]; then
  exit 0
fi
# shellcheck disable=SC1090
. "$LOCAL_CONFIG"

WARNINGS=""

# Superchart (covers SUPERCHART_API.md and SUPERCHART_USAGE.md)
if [ -f "$DEPS_DIR/SUPERCHART_API.md" ] && [ -n "$SUPERCHART_DIR" ] && [ -d "$SUPERCHART_DIR" ]; then
  EXPECTED_SC=$(grep 'Git hash:' "$DEPS_DIR/SUPERCHART_API.md" 2>/dev/null | sed 's/.*`\([a-f0-9]*\)`.*/\1/')
  ACTUAL_SC=$(git -C "$SUPERCHART_DIR" rev-parse HEAD 2>/dev/null)
  if [ -n "$EXPECTED_SC" ] && [ -n "$ACTUAL_SC" ] && [ "$ACTUAL_SC" != "$EXPECTED_SC" ]; then
    WARNINGS="STALE: Superchart docs outdated (expected ${EXPECTED_SC:0:12}, repo is ${ACTUAL_SC:0:12}). Explore changed files and update docs before proceeding."
  fi
fi

# CoinrayJS
if [ -f "$DEPS_DIR/COINRAYJS_API.md" ] && [ -n "$COINRAYJS_DIR" ] && [ -d "$COINRAYJS_DIR" ]; then
  EXPECTED_CJ=$(grep 'Git hash:' "$DEPS_DIR/COINRAYJS_API.md" 2>/dev/null | sed 's/.*`\([a-f0-9]*\)`.*/\1/')
  ACTUAL_CJ=$(git -C "$COINRAYJS_DIR" rev-parse HEAD 2>/dev/null)
  if [ -n "$EXPECTED_CJ" ] && [ -n "$ACTUAL_CJ" ] && [ "$ACTUAL_CJ" != "$EXPECTED_CJ" ]; then
    WARNINGS="${WARNINGS:+$WARNINGS
}STALE: CoinrayJS docs outdated (expected ${EXPECTED_CJ:0:12}, repo is ${ACTUAL_CJ:0:12}). Explore changed files and update docs before proceeding."
  fi
fi

if [ -n "$WARNINGS" ]; then
  echo "$WARNINGS"
fi

exit 0
