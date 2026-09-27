# Geo Guess

![Geo Guess](preview.png)

Geo Guess is a Omarchy plugin that puts a globe on your bar. Pick a spot to open nearby Street View, or play a round and guess where you are. Enjoy.

---

# AI written

## Install

```sh
omarchy plugin add https://github.com/LessUnderRated/geoguess.git --enable
```

## Usage

Click the globe on the bar to open or close the panel. Press Escape to close it.

## Configure

Guess chrome lives in `guess-hide/`. Load that folder yourself with Chromium `--load-extension` if you want it. The optional native host is `scripts/install-guess-host.sh`. Neither runs on plugin add.

## Remove

```sh
omarchy plugin remove lessunderrated.geoguess
```
