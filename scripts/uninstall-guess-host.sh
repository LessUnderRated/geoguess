#!/usr/bin/env bash
# Remove only Geo Guess native-messaging host files this plugin still owns.
set -euo pipefail
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
exec /usr/bin/python3 "$plugin_dir/uninstall.py" remove-host
