#!/usr/bin/env bash
# Remove the optional Geo Guess native-messaging host files this plugin
# installs. Does not change Chromium flags or other configuration.
set -euo pipefail
removed=0
for dest in \
  "$HOME/.config/chromium/NativeMessagingHosts/com.lessunderrated.geoguess.json" \
  "$HOME/.config/chromium/Default/NativeMessagingHosts/com.lessunderrated.geoguess.json"
do
  if [[ -f $dest ]]; then
    rm -f "$dest"
    removed=1
  fi
done
if [[ $removed -eq 1 ]]; then
  echo "Removed com.lessunderrated.geoguess native-messaging host"
else
  echo "No Geo Guess native-messaging host files found"
fi
