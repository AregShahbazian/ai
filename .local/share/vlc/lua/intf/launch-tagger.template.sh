#!/bin/bash
# Clip-tagger launcher TEMPLATE — copy into any clips root folder as
# launch-tagger.sh (chmod +x) to make that folder a taggable library:
#
#   cp ~/.local/share/vlc/lua/intf/launch-tagger.template.sh <clips-root>/launch-tagger.sh
#   chmod +x <clips-root>/launch-tagger.sh
#
# Starts VLC on the folder it lives in, with tagging hotkeys enabled.
# Exports the root + db location; rotate_hotkey.lua (VLC lua intf) picks them
# up via os.getenv and enables the t (tags) / i (attributes) dialogs.
ROOT="$(cd "$(dirname "$0")" && pwd)"
export CLIPTAG_ROOT="$ROOT"
export CLIPTAG_DB="$ROOT/cliptags.json"
exec vlc "$ROOT" "$@"
