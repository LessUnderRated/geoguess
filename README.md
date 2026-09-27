# Geo Guess

A globe with a details panel for the Omarchy Quattro bar. Pick a spot to open nearby Street View, or play a round and guess where you are.

## Install

```sh
omarchy plugin add https://github.com/LessUnderRated/geoguess.git --enable
```

The plugin id is `lessunderrated.geoguess`. Enabling it only adds a bar widget. It does not change Chromium flags, native-messaging hosts, or other user configuration.

## Usage

Click the globe on the bar to open or close the panel. Press Escape to close it.

```sh
omarchy-shell shell summon lessunderrated.geoguess '{}'
omarchy-shell shell hide lessunderrated.geoguess
```

## Configure

```sh
omarchy bar move lessunderrated.geoguess --section right
```

Guess rounds that hide Maps chrome use an unpacked Chromium extension in `guess-hide/`. That is optional and only used if you add the path yourself to Chromium `--load-extension` (for example in `~/.config/chromium-flags.conf`):

```text
$HOME/.config/omarchy/plugins/lessunderrated.geoguess/guess-hide
```

Fully quit Chromium after changing that flag. New round still works if the native messaging host is missing.

The native host is also optional. It only writes Chromium host files if you run:

```sh
bash "$HOME/.config/omarchy/plugins/lessunderrated.geoguess/scripts/install-guess-host.sh"
```

## Remove

```sh
omarchy plugin remove lessunderrated.geoguess
```

If you installed the optional host:

```sh
bash "$HOME/.config/omarchy/plugins/lessunderrated.geoguess/scripts/uninstall-guess-host.sh"
```

If you added `guess-hide` to Chromium flags, remove that path yourself. The plugin never edits those flags.

## License and dependencies

MIT. Author: LessUnderRated.

External dependencies (no extra packages are installed by the plugin):

- Omarchy / Quickshell (bar widget)
- Python 3 standard library (`streetview-lookup`, `guess-host`)
- Network access to Google Maps / Street View coverage endpoints
- `omarchy-launch-webapp` and Hyprland (`hyprctl`) to open and fullscreen the Street View window
- Optional: Chromium with the unpacked `guess-hide` extension and native messaging host `com.lessunderrated.geoguess`

Privilege boundary: the plugin runs inside the unsandboxed Omarchy shell with your user permissions. Opening a round launches a Chromium webapp and may fullscreen that window. No sudo or pkexec is required. No install hook runs on `omarchy plugin add`.
