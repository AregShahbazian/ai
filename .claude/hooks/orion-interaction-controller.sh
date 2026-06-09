#!/usr/bin/env bash
# Orion convention enforcer (advisory): every meaningful user action must route
# through InteractionController.dispatch (see ai/mvp/phase-3/interaction-controller/).
#
# Fires on PostToolUse(Edit|Write). Scans the edited lib/**.dart file for INLINE
# interaction-handler closures (onTap/onPressed/onChanged/onLongPress/onSelected/
# onDoubleTap) whose body does NOT mention dispatch/InteractionController, and
# surfaces them back to Claude as advisory context so they get reviewed/fixed.
#
# Deliberately ignores tear-offs (`onPressed: onPressed`, `onPressed: _handler`)
# and prop-forwarding closures (`() => widget.onTap?.call()`) — those are how
# presentational widgets pass a callback through, not a bypass.
set -euo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null || true)"

# Only Dart widget files under lib/. Skip the controller itself and tests.
case "$file" in
  */lib/*.dart) ;;
  *) exit 0 ;;
esac
case "$file" in
  *interaction_controller.dart|*_test.dart) exit 0 ;;
esac
[ -f "$file" ] || exit 0

findings="$(awk '
  { lines[NR] = $0 }
  END {
    for (i = 1; i <= NR; i++) {
      line = lines[i]
      # Inline handler closure opener: on<Handler>: ( ... ) => | {
      if (line ~ /on(Tap|DoubleTap|Pressed|Changed|LongPress|Selected)[ \t]*:[ \t]*\([^)]*\)[ \t]*(=>|\{)/) {
        # Prop-forwarding closure (one-liner) -> not a bypass, skip. Checked on
        # the opener line only, so a sibling forward below cannot mask a real one.
        if (line ~ /\.call\(/ || line ~ /=>[ \t]*widget\./) continue
        # Routed through the bus -> fine. Window = opener + next 3 lines, since a
        # dispatch chain (InteractionController.instance\n  .dispatch(...)) spans
        # a couple lines. Kept short to limit bleed into sibling handlers.
        window = line
        for (j = i + 1; j <= NR && j <= i + 3; j++) window = window "\n" lines[j]
        if (window ~ /dispatch\(/ || window ~ /InteractionController/) continue
        s = line; sub(/^[ \t]+/, "", s)
        printf "  line %d: %s\n", i, s
      }
    }
  }
' "$file")"

[ -z "$findings" ] && exit 0

rel="${file#"$PWD"/}"
msg="Orion convention check: $rel has inline interaction handler(s) that do NOT route through InteractionController.dispatch:
$findings
Per ai/mvp/phase-3/interaction-controller/design.md, every meaningful user action must dispatch through the bus (both-ways: capturable + programmatically dispatchable). Route these through InteractionController.instance.dispatch(...). If a flagged line is genuinely not a user action (e.g. a builder/local-state callback) or a presentational forward, ignore it."

# Surface as advisory context to Claude; show the user a one-line note.
jq -n --arg ctx "$msg" --arg sys "Orion: interaction-controller check flagged $rel" \
  '{systemMessage: $sys, hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
exit 0
