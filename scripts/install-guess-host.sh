#!/usr/bin/env bash
# Register Geo Guess's native-messaging host without overwriting another host.
set -euo pipefail
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
host="$plugin_dir/guess-host"
if [[ ! -x $host ]]; then
  echo "missing executable host: $host" >&2
  exit 1
fi
exec /usr/bin/python3 "$plugin_dir/uninstall.py" install-host "$host"
