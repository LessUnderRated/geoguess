#!/usr/bin/env python3
"""Install or remove Geo Guess Chromium bits.

Disable: strip --load-extension and native-host files. Keep the plugin folder
and Chromium extension settings so enable can put the flag back.

Remove: that, plus this extension's Chromium profile data, the helper copy,
and the user systemd path that watches for a deleted plugin folder.
"""
import json
import os
import shutil
import subprocess
import sys

HOME = os.environ.get("HOME", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
PLUGIN_ID = "lessunderrated.geoguess"
PLUGIN_DIR = os.path.join(XDG_CONFIG, "omarchy", "plugins", PLUGIN_ID)
EXTENSION_DIR = os.path.join(PLUGIN_DIR, "guess-hide")
UNINSTALL_DST = os.path.join(XDG_CONFIG, "omarchy", f"{PLUGIN_ID}.uninstall.py")
MARKER = "lessunderrated.geoguess/guess-hide"
HOST_NAME = "com.lessunderrated.geoguess.json"
EXTENSION_ID = "ghhlkacefalngacompmfpiekbmblamgg"
UNIT = "lessunderrated-geoguess-gone"
FLAG_FILES = (
    os.path.join(XDG_CONFIG, "chromium-flags.conf"),
    os.path.join(XDG_CONFIG, "chromium", "chromium-flags.conf"),
)
HOST_FILES = (
    os.path.join(XDG_CONFIG, "chromium", "NativeMessagingHosts", HOST_NAME),
    os.path.join(XDG_CONFIG, "chromium", "Default", "NativeMessagingHosts", HOST_NAME),
)
BROWSER_CONFIGS = (
    os.path.join(XDG_CONFIG, "chromium"),
    os.path.join(XDG_CONFIG, "google-chrome"),
    os.path.join(XDG_CONFIG, "google-chrome-unstable"),
    os.path.join(XDG_CONFIG, "BraveSoftware", "Brave-Browser"),
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
                continue
            out.append(join_line(filtered) + keepends)
        if add and not seen and os.path.isdir(EXTENSION_DIR):
            if out and not "".join(out).endswith("\n"):
                out.append("\n")
            out.append(join_line([EXTENSION_DIR]) + "\n")
        next_text = "".join(out)
        if next_text != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(next_text)


def remove_hosts():
    for path in HOST_FILES:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def chromium_running():
    for name in ("chromium", "chrome", "brave"):
        try:
            if subprocess.run(
                ["pgrep", "-x", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode == 0:
                return True
        except OSError:
            continue
    return False


def profile_dirs(root):
    if not os.path.isdir(root):
        return
    for name in os.listdir(root):
        if name == "Default" or name.startswith("Profile "):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                yield path


def rm_tree(path):
    shutil.rmtree(path, ignore_errors=True)


def scrub_preferences(prefs_path):
    if chromium_running() or not os.path.isfile(prefs_path):
        return
    try:
        with open(prefs_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return
    ext = data.get("extensions")
    if not isinstance(ext, dict):
        return
    changed = False
    for key in ("settings", "install_signature"):
        bucket = ext.get(key)
        if isinstance(bucket, dict) and EXTENSION_ID in bucket:
            del bucket[EXTENSION_ID]
            changed = True
    pinned = data.get("extensions", {}).get("pinned_extensions")
    if isinstance(pinned, list) and EXTENSION_ID in pinned:
        data["extensions"]["pinned_extensions"] = [x for x in pinned if x != EXTENSION_ID]
        changed = True
    if not changed:
        return
    try:
        with open(prefs_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, separators=(",", ":"))
    except OSError:
        pass


def remove_extension_profile():
    for root in BROWSER_CONFIGS:
        for profile in profile_dirs(root):
            rm_tree(os.path.join(profile, "Local Extension Settings", EXTENSION_ID))
            rm_tree(os.path.join(profile, "Sync Extension Settings", EXTENSION_ID))
            rm_tree(os.path.join(profile, "Extension Rules", EXTENSION_ID))
            rm_tree(os.path.join(profile, "Extension Scripts", EXTENSION_ID))
            rm_tree(os.path.join(profile, "Extension State", EXTENSION_ID))
            rm_tree(
                os.path.join(
                    profile,
                    "IndexedDB",
                    "chrome-extension_" + EXTENSION_ID + "_0.indexeddb.leveldb",
                )
            )
            rm_tree(
                os.path.join(
                    profile,
                    "IndexedDB",
                    "chrome-extension_" + EXTENSION_ID + "_0.indexeddb.blob",
                )
            )
            storage = os.path.join(profile, "Storage", "ext", EXTENSION_ID)
            rm_tree(storage)
            scrub_preferences(os.path.join(profile, "Preferences"))


def unit_dir():
    return os.path.join(XDG_CONFIG, "systemd", "user")


def install_watch():
    directory = unit_dir()
    os.makedirs(directory, exist_ok=True)
    service = os.path.join(directory, UNIT + ".service")
    path_unit = os.path.join(directory, UNIT + ".path")
    with open(service, "w", encoding="utf-8") as fh:
        fh.write(
            "[Unit]\n"
            "Description=Finish Geo Guess Chromium cleanup after plugin remove\n"
            "[Service]\n"
            "Type=oneshot\n"
            "ExecStart=/usr/bin/python3 %s --remove-if-missing\n" % UNINSTALL_DST
        )
    with open(path_unit, "w", encoding="utf-8") as fh:
        fh.write(
            "[Unit]\n"
            "Description=Watch for Geo Guess plugin folder removal\n"
            "[Path]\n"
            "PathModified=%s\n" % os.path.join(XDG_CONFIG, "omarchy", "plugins")
            + "[Install]\n"
            "WantedBy=default.target\n"
        )
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", UNIT + ".path"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def remove_watch():
    try:
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", UNIT + ".path", UNIT + ".service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass
    directory = unit_dir()
    for name in (UNIT + ".path", UNIT + ".service"):
        try:
            os.remove(os.path.join(directory, name))
        except FileNotFoundError:
            pass


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


def light_clean():
    rewrite_flags(remove=True)
    remove_hosts()


def full_clean():
    light_clean()
    remove_extension_profile()
    remove_watch()
    try:
        os.remove(UNINSTALL_DST)
    except FileNotFoundError:
        pass


def cmd_setup():
    install_copy()
    install_watch()
    rewrite_flags(add=True)
    print("ok")
    return 0


def cmd_disable():
    if "--unless-enabled" in sys.argv and plugin_is_enabled_in_shell_config():
        print("skip")
        return 0
    light_clean()
    print("ok")
    return 0


def cmd_remove():
    if "--remove-if-missing" in sys.argv and os.path.isdir(PLUGIN_DIR):
        print("skip")
        return 0
    if "--unless-enabled" in sys.argv and plugin_is_enabled_in_shell_config():
        print("skip")
        return 0
    full_clean()
    print("ok")
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ["setup"]:
        return cmd_setup()
    if "--remove" in args or "--remove-if-missing" in args:
        return cmd_remove()
    if not os.path.isdir(PLUGIN_DIR):
        return cmd_remove()
    return cmd_disable()


if __name__ == "__main__":
    sys.exit(main())
