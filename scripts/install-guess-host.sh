#!/usr/bin/env bash
# Register the Geo Guess native-messaging host for the current user.
set -euo pipefail
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
host="$plugin_dir/guess-host"
if [[ ! -x $host ]]; then
  echo "missing executable host: $host" >&2
  exit 1
fi
manifest=$(cat <<EOF
{
  "name": "com.lessunderrated.geoguess",
  "description": "Geo Guess next-round helper",
  "path": "$host",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"]
}
EOF
)
for dest in \
  "$HOME/.config/chromium/NativeMessagingHosts" \
  "$HOME/.config/chromium/Default/NativeMessagingHosts"
do
  mkdir -p "$dest"
  printf '%s\n' "$manifest" > "$dest/com.lessunderrated.geoguess.json"
done
echo "Writes Chromium native-messaging host files under \$HOME/.config/chromium."
echo "Does not change Chromium flags or any other configuration."
echo "Registered com.lessunderrated.geoguess"
