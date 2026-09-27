#!/usr/bin/env python3
"""Install or remove Geo Guess Chromium bits.

`setup` copies this script outside the plugin folder (so `omarchy plugin remove`
can still run it) and adds guess-hide to chromium-flags.conf.

`teardown` / default / `--unless-enabled` removes that extension path and the
native-messaging host files.
"""
import json
import os
import shutil
import sys

HOME = os.environ.get("HOME", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
PLUGIN_ID = "lessunderrated.geoguess"
PLUGIN_DIR = os.path.join(XDG_CONFIG, "omarchy", "plugins", PLUGIN_ID)
EXTENSION_DIR = os.path.join(PLUGIN_DIR, "guess-hide")
UNINSTALL_DST = os.path.join(XDG_CONFIG, "omarchy", f"{PLUGIN_ID}.uninstall.py")
MARKER = "lessunderrated.geoguess/guess-hide"
HOST_NAME = "com.lessunderrated.geoguess.json"
FLAG_FILES = (
    os.path.join(XDG_CONFIG, "chromium-flags.conf"),
    os.path.join(XDG_CONFIG, "chromium", "chromium-flags.conf"),
)
HOST_FILES = (
    os.path.join(XDG_CONFIG, "chromium", "NativeMessagingHosts", HOST_NAME),
    os.path.join(XDG_CONFIG, "chromium", "Default", "NativeMessagingHosts", HOST_NAME),
)


def plugin_is_enabled_in_shell_config():
    path = os.path.join(XDG_CONFIG, "omarchy", "shell.json")
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, ValueError):
        return False
    if PLUGIN_ID in (config.get("disabledPlugins") or []):
        return False

    def found(node):
        if isinstance(node, dict):
            if node.get("id") == PLUGIN_ID:
                return True
            return any(found(value) for value in node.values())
        if isinstance(node, list):
            return any(found(item) for item in node)
        return False

    return found(config.get("bar")) or found(config.get("plugins")) or found(config.get("layout"))


def split_extensions(value):
    raw = value.split("=", 1)[-1].strip()
    if not raw:
        return []
    return [part for part in raw.split(",") if part]


def join_line(paths):
    return "--load-extension=" + ",".join(paths)


def rewrite_flags(add=False, remove=False):
    changed = False
    for path in FLAG_FILES:
        try:
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if not text:
            continue
        lines = text.splitlines(keepends=True)
        out = []
        seen = False
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("--load-extension="):
                out.append(line)
                continue
            seen = True
            keepends = line[len(line.rstrip("\r\n")) :]
            paths = split_extensions(stripped)
            filtered = [p for p in paths if MARKER not in p.replace("\\", "/")]
            if add and os.path.isdir(EXTENSION_DIR):
                if not any(MARKER in p.replace("\\", "/") for p in filtered):
                    filtered.append(EXTENSION_DIR)
            if remove:
                filtered = [p for p in filtered if MARKER not in p.replace("\\", "/")]
            if not filtered:
                changed = True
                continue
            new = join_line(filtered) + keepends
            if new != line:
                changed = True
            out.append(new)
        if add and not seen and os.path.isdir(EXTENSION_DIR):
            if out and not "".join(out).endswith("\n"):
                out.append("\n")
            out.append(join_line([EXTENSION_DIR]) + "\n")
            changed = True
        next_text = "".join(out)
        if next_text != text:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(next_text)
            changed = True
    return changed


def remove_hosts():
    removed = False
    for path in HOST_FILES:
        try:
            os.remove(path)
            removed = True
        except FileNotFoundError:
            pass
    return removed


def install_copy():
    src = os.path.join(PLUGIN_DIR, "uninstall.py")
    if not os.path.isfile(src):
        src = os.path.abspath(__file__)
    if not os.path.isfile(src):
        return False
    os.makedirs(os.path.dirname(UNINSTALL_DST), exist_ok=True)
    shutil.copy2(src, UNINSTALL_DST)
    os.chmod(UNINSTALL_DST, 0o755)
    return True


def cmd_setup():
    install_copy()
    rewrite_flags(add=True)
    print("ok")
    return 0


def cmd_teardown():
    if "--unless-enabled" in sys.argv and plugin_is_enabled_in_shell_config():
        print("skip")
        return 0
    rewrite_flags(remove=True)
    remove_hosts()
    try:
        os.remove(UNINSTALL_DST)
    except FileNotFoundError:
        pass
    print("ok")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        return cmd_setup()
    return cmd_teardown()


if __name__ == "__main__":
    sys.exit(main())
