# Geo Guess

![Geo Guess](preview.png)

GeoGuess is a google streetview explorer and geolocation game, that uses a chromium extension to locally modify google streetview using no other apis or keys.

---

# AI written

## Install

```sh
omarchy plugin add https://github.com/LessUnderRated/geoguess.git --enable
```

## Usage

Click the globe on the bar to open or close the panel. Press Escape to close it.

## Configure

Guess chrome lives in `guess-hide/`. Enabling the plugin adds that folder to Chromium `--load-extension`. Disable or `omarchy plugin remove` takes it back out and deletes the optional native-messaging host. Fully quit Chromium after either change.

Needs Python 3, network access to Google Maps / Street View, and `omarchy-launch-webapp`. No sudo.

## Remove

```sh
omarchy plugin remove lessunderrated.geoguess
```
