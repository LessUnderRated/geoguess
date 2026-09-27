#!/usr/bin/env bash
# Register Geo Guess's native-messaging host without overwriting another host.
set -euo pipefail
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
host="$plugin_dir/guess-host"
if [[ ! -x $host ]]; then
  echo "missing executable host: $host" >&2
  exit 1
fi
for dest in \
  "$HOME/.config/chromium/NativeMessagingHosts" \
  "$HOME/.config/chromium/Default/NativeMessagingHosts"
do
  mkdir -p "$dest"
  file="$dest/com.lessunderrated.geoguess.json"
  if [[ -e $file && ! -f $file || -L $file ]]; then
    echo "refusing to modify non-regular host path: $file" >&2
    exit 1
  fi
  if [[ -f $file ]] && ! grep -q '"x-omarchy-owner": "lessunderrated.geoguess"' "$file"; then
    echo "refusing to overwrite unowned host file: $file" >&2
    exit 1
  fi
  tmp=$(mktemp "$dest/.geoguess-host.XXXXXX")
  trap 'rm -f "$tmp"' EXIT
  cat > "$tmp" <<EOF
{
  "x-omarchy-owner": "lessunderrated.geoguess",
  "name": "com.lessunderrated.geoguess",
  "description": "Geo Guess next-round helper",
  "path": "$host",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"]
}
EOF
  chmod 600 "$tmp"
  mv -f -- "$tmp" "$file"
  trap - EXIT
done
echo "Registered com.lessunderrated.geoguess"
