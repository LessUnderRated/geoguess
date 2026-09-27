#!/usr/bin/env python3
"""Manage Geo Guess runtime state without touching unrelated user configuration.

Only files containing Geo Guess ownership markers are changed or removed. Browser
profile data is intentionally left untouched; Chromium owns that configuration.
"""
import json
import os
import subprocess
import sys
import tempfile

HOME = os.environ.get("HOME", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
PLUGIN_ID = "lessunderrated.geoguess"
PLUGIN_DIR = os.path.join(XDG_CONFIG, "omarchy", "plugins", PLUGIN_ID)
EXTENSION_DIR = os.path.join(PLUGIN_DIR, "guess-hide", "unpacked")
UNINSTALL_DST = os.path.join(XDG_CONFIG, "omarchy", f"{PLUGIN_ID}.uninstall.py")
HOST_NAME = "com.lessunderrated.geoguess.json"
EXTENSION_ID = "ghhlkacefalngacompmfpiekbmblamgg"
UNIT = "lessunderrated-geoguess-gone"
OWNED_LINE = "# Owned-by: lessunderrated.geoguess"
HOST_OWNER = "lessunderrated.geoguess"
FLAG_FILES = (
    os.path.join(XDG_CONFIG, "chromium-flags.conf"),
    os.path.join(XDG_CONFIG, "chromium", "chromium-flags.conf"),
)
HOST_FILES = (
    os.path.join(XDG_CONFIG, "chromium", "NativeMessagingHosts", HOST_NAME),
    os.path.join(XDG_CONFIG, "chromium", "Default", "NativeMessagingHosts", HOST_NAME),
)


def regular(path):
    """Return true only for a non-symlink regular file."""
    return os.path.isfile(path) and not os.path.islink(path)


def atomic_write(path, text, mode=None):
    """Replace our regular file without following links or leaving partial data."""
    if os.path.lexists(path) and not regular(path):
        return False
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    if mode is None and regular(path):
        mode = os.stat(path).st_mode & 0o777
    if mode is None:
        mode = 0o600
    fd, temporary = tempfile.mkstemp(prefix=".geoguess-", dir=directory, text=True)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, path)
        return True
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


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


def extension_path(path):
    return os.path.normpath(path).replace("\\", "/") == os.path.normpath(EXTENSION_DIR).replace("\\", "/")


def rewrite_flags(add=False, remove=False):
    for path in FLAG_FILES:
        if not regular(path):
            continue
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except OSError:
            continue
        lines = text.splitlines(keepends=True)
        out = []
        found = False
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("--load-extension="):
                out.append(line)
                continue
            found = True
            ending = line[len(line.rstrip("\r\n")):]
            value = stripped.split("=", 1)[1]
            paths = [item for item in value.split(",") if item]
            if remove:
                paths = [item for item in paths if not extension_path(item)]
            if add and os.path.isdir(EXTENSION_DIR) and EXTENSION_DIR not in paths:
                paths.append(EXTENSION_DIR)
            if paths:
                out.append("--load-extension=" + ",".join(paths) + ending)
        if add and not found and os.path.isdir(EXTENSION_DIR):
            if out and not "".join(out).endswith("\n"):
                out.append("\n")
            out.append("--load-extension=" + EXTENSION_DIR + "\n")
        next_text = "".join(out)
        if next_text != text:
            atomic_write(path, next_text)


def host_matches(path):
    if not regular(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    return (
        data.get("x-omarchy-owner") == HOST_OWNER
        and data.get("name") == "com.lessunderrated.geoguess"
        and data.get("path") == os.path.join(PLUGIN_DIR, "guess-host")
        and data.get("allowed_origins") == ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"]
    )


def remove_hosts():
    for path in HOST_FILES:
        if host_matches(path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


def chromium_running():
    for name in ("chromium", "chrome", "brave"):
        try:
            if subprocess.run(["pgrep", "-x", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return True
        except OSError:
            pass
    return False


def unit_dir():
    return os.path.join(XDG_CONFIG, "systemd", "user")


def we_own(path):
    if not regular(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return OWNED_LINE in fh.read()
    except OSError:
        return False


def write_owned(path, body):
    text = OWNED_LINE + "\n" + body
    if os.path.lexists(path) and not we_own(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return True
    except OSError:
        pass
    return atomic_write(path, text, 0o600)


def remove_owned(path):
    if not we_own(path):
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def install_watch():
    directory = unit_dir()
    service = os.path.join(directory, UNIT + ".service")
    path_unit = os.path.join(directory, UNIT + ".path")
    wrote_service = write_owned(
        service,
        "[Unit]\nDescription=Finish Geo Guess Chromium cleanup after plugin remove\n"
        "[Service]\nType=oneshot\nExecStart=/usr/bin/python3 %s --sync\n" % UNINSTALL_DST,
    )
    wrote_path = write_owned(
        path_unit,
        "[Unit]\nDescription=Watch for Geo Guess plugin folder removal\n[Path]\n"
        "PathModified=%s\nPathModified=%s\n[Install]\nWantedBy=default.target\n"
        % (os.path.join(XDG_CONFIG, "omarchy", "plugins"), os.path.join(XDG_CONFIG, "omarchy", "shell.json")),
    )
    if not (wrote_service and wrote_path):
        return
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", UNIT + ".path"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def remove_watch():
    service = os.path.join(unit_dir(), UNIT + ".service")
    path_unit = os.path.join(unit_dir(), UNIT + ".path")
    if not ((not os.path.lexists(service) or we_own(service)) and (not os.path.lexists(path_unit) or we_own(path_unit))):
        return
    try:
        subprocess.run(["systemctl", "--user", "disable", "--now", UNIT + ".path", UNIT + ".service"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass
    remove_owned(service)
    remove_owned(path_unit)


def install_copy():
    src = os.path.join(PLUGIN_DIR, "uninstall.py")
    if not regular(src):
        src = os.path.abspath(__file__)
    if not regular(src):
        return False
    if os.path.lexists(UNINSTALL_DST) and not we_own(UNINSTALL_DST):
        return False
    try:
        with open(src, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return False
    if not content.startswith("#!/usr/bin/env python3"):
        return False
    return atomic_write(UNINSTALL_DST, content, 0o755)


def remove_copy():
    remove_owned(UNINSTALL_DST)


def light_clean():
    rewrite_flags(remove=True)
    remove_hosts()


def full_clean():
    light_clean()
    remove_watch()
    remove_copy()


def cmd_setup():
    if not install_copy():
        print("Geo Guess refused to replace an unowned uninstall script", file=sys.stderr)
        return 1
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


def cmd_sync():
    if not os.path.isdir(PLUGIN_DIR):
        full_clean()
        print("ok")
        return 0
    if plugin_is_enabled_in_shell_config():
        rewrite_flags(add=True)
        print("enabled")
        return 0
    light_clean()
    print("disabled")
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ["setup"]:
        return cmd_setup()
    if "--sync" in args:
        return cmd_sync()
    if "--remove" in args or "--remove-if-missing" in args:
        return cmd_remove()
    if not os.path.isdir(PLUGIN_DIR):
        return cmd_remove()
    return cmd_disable()


if __name__ == "__main__":
    sys.exit(main())
