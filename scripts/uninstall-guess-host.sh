#!/usr/bin/env bash
# Remove only Geo Guess native-messaging host files that carry our ownership marker.
set -euo pipefail
removed=0
for dest in \
  "$HOME/.config/chromium/NativeMessagingHosts/com.lessunderrated.geoguess.json" \
  "$HOME/.config/chromium/Default/NativeMessagingHosts/com.lessunderrated.geoguess.json"
do
  if [[ -L $dest || ! -f $dest ]]; then
    continue
  fi
  if grep -q '"x-omarchy-owner": "lessunderrated.geoguess"' "$dest" \
    && grep -q '"name": "com.lessunderrated.geoguess"' "$dest"; then
    rm -- "$dest"
    removed=1
  fi
done
if [[ $removed -eq 1 ]]; then
  echo "Removed owned Geo Guess native-messaging host"
else
  echo "No owned Geo Guess native-messaging host files found"
fi
