#!/usr/bin/env python3
"""Manage Geo Guess runtime state without deleting user-modified files."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HOME = os.environ.get("HOME", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
# Omarchy's PluginRegistry and plugin catalog always use ~/.config/omarchy,
# even when XDG_CONFIG_HOME points somewhere else. Chromium and systemd follow XDG.
OMARCHY_CONFIG = os.path.join(HOME, ".config", "omarchy")
PLUGIN_ID = "lessunderrated.geoguess"
PLUGIN_DIR = os.path.join(OMARCHY_CONFIG, "plugins", PLUGIN_ID)
EXTENSION_DIR = os.path.join(PLUGIN_DIR, "guess-hide", "unpacked")
UNINSTALL_DST = os.path.join(OMARCHY_CONFIG, f"{PLUGIN_ID}.uninstall.py")
MAX_CONFIG_BYTES = 1024 * 1024
OWNER_RECORD = UNINSTALL_DST + ".owner"
HOST_NAME = "com.lessunderrated.geoguess.json"
EXTENSION_ID = "ghhlkacefalngacompmfpiekbmblamgg"
UNIT = "lessunderrated-geoguess-gone"
OWNED_PREFIX = "# Owned-by: lessunderrated.geoguess sha256="
HOST_OWNER = "lessunderrated.geoguess"
FLAG_FILES = (os.path.join(XDG_CONFIG, "chromium-flags.conf"), os.path.join(XDG_CONFIG, "chromium", "chromium-flags.conf"))
HOST_FILES = (os.path.join(XDG_CONFIG, "chromium", "NativeMessagingHosts", HOST_NAME), os.path.join(XDG_CONFIG, "chromium", "Default", "NativeMessagingHosts", HOST_NAME))


def regular(path):
    return os.path.isfile(path) and not os.path.islink(path)


def atomic_write(path, text, mode=None):
    if os.path.lexists(path) and not regular(path):
        return False
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    if mode is None and regular(path):
        mode = os.stat(path).st_mode & 0o777
    mode = 0o600 if mode is None else mode
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


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def owner_record(content):
    """Sidecar token for the copied uninstall script. Always includes a trailing newline."""
    return digest(content or "") + "\n"


def owned_text(body):
    return OWNED_PREFIX + digest(body) + "\n" + body


def read_text(path, limit=MAX_CONFIG_BYTES):
    try:
        with open(path, "rb") as fh:
            data = fh.read(limit + 1)
    except OSError:
        return None
    if len(data) > limit:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def plugin_is_enabled_in_shell_config():
    path = os.path.join(OMARCHY_CONFIG, "shell.json")
    text = read_text(path)
    if text is None:
        try:
            return os.path.isfile(path) and os.path.getsize(path) > MAX_CONFIG_BYTES
        except OSError:
            return False
    try:
        config = json.loads(text)
    except ValueError:
        return False
    if PLUGIN_ID in (config.get("disabledPlugins") or []):
        return False
    def found(node):
        if isinstance(node, dict):
            return node.get("id") == PLUGIN_ID or any(found(v) for v in node.values())
        return isinstance(node, list) and any(found(v) for v in node)
    return found(config.get("bar")) or found(config.get("plugins")) or found(config.get("layout"))


def extension_path(path):
    return os.path.normpath(path).replace("\\", "/") == os.path.normpath(EXTENSION_DIR).replace("\\", "/")


def rewrite_flags(add=False, remove=False):
    for path in FLAG_FILES:
        if not regular(path):
            continue
        text = read_text(path)
        if text is None:
            continue
        lines, out, ours = text.splitlines(keepends=True), [], False
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("--load-extension="):
                out.append(line); continue
            ending = line[len(line.rstrip("\r\n")):]
            paths = [p for p in stripped.split("=", 1)[1].split(",") if p]
            if remove:
                paths = [p for p in paths if not extension_path(p)]
            elif add and os.path.isdir(EXTENSION_DIR) and EXTENSION_DIR in paths:
                ours = True
            if paths: out.append("--load-extension=" + ",".join(paths) + ending)
        if add and not ours and os.path.isdir(EXTENSION_DIR):
            if out and not "".join(out).endswith("\n"): out.append("\n")
            out.append("--load-extension=" + EXTENSION_DIR + "\n")
        updated = "".join(out)
        if updated != text: atomic_write(path, updated)


def host_payload(host_bin):
    return {
        "allowed_origins": ["chrome-extension://%s/" % EXTENSION_ID],
        "description": "Geo Guess next-round helper",
        "name": "com.lessunderrated.geoguess",
        "path": host_bin,
        "type": "stdio",
        "x-omarchy-owner": HOST_OWNER,
    }


def canonical_host_body(payload):
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def owned_host_text(host_bin):
    payload = host_payload(host_bin)
    stamped = dict(payload)
    stamped["x-omarchy-sha256"] = digest(canonical_host_body(payload))
    return json.dumps(stamped, indent=2, sort_keys=True) + "\n"


def we_own_host(path):
    """Own only an exact host registration we generate, not a user-edited copy."""
    if not regular(path):
        return False
    text = read_text(path)
    if text is None:
        return False
    try:
        data = json.loads(text)
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    host_bin = data.get("path")
    if not isinstance(host_bin, str) or not host_bin:
        return False
    if text == owned_host_text(host_bin):
        return True
    normalized = os.path.normpath(host_bin)
    if os.path.basename(normalized) != "guess-host" or PLUGIN_ID not in normalized.split(os.sep):
        return False
    return data == host_payload(host_bin)


def write_host(path, host_bin):
    text = owned_host_text(host_bin)
    if os.path.lexists(path) and not we_own_host(path):
        return False
    if read_text(path) == text:
        return True
    return atomic_write(path, text, 0o600)


def install_hosts(host_bin):
    if not regular(host_bin) or not os.access(host_bin, os.X_OK):
        print("missing executable host: %s" % host_bin, file=sys.stderr)
        return False
    ok = True
    for path in HOST_FILES:
        if not write_host(path, host_bin):
            print("refusing to overwrite unowned host file: %s" % path, file=sys.stderr)
            ok = False
    return ok


def remove_hosts():
    removed = False
    for path in HOST_FILES:
        if not we_own_host(path):
            continue
        try:
            os.remove(path)
            removed = True
        except FileNotFoundError:
            pass
    return removed


def unit_dir(): return os.path.join(XDG_CONFIG, "systemd", "user")


def we_own(path):
    """Ownership is a content digest, not a marker that a user can retain after editing."""
    if not regular(path): return False
    text = read_text(path)
    if text is None or "\n" not in text: return False
    header, body = text.split("\n", 1)
    return header == OWNED_PREFIX + digest(body)


def write_owned(path, body):
    text = owned_text(body)
    if os.path.lexists(path) and not we_own(path): return False
    if read_text(path) == text: return True
    return atomic_write(path, text, 0o600)


def remove_owned(path):
    if not we_own(path): return
    try: os.remove(path)
    except FileNotFoundError: pass


def install_watch():
    directory = unit_dir()
    service = os.path.join(directory, UNIT + ".service")
    path_unit = os.path.join(directory, UNIT + ".path")
    service_body = "[Unit]\nDescription=Finish Geo Guess Chromium cleanup after plugin remove\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 %s --sync\n" % UNINSTALL_DST
    path_body = "[Unit]\nDescription=Watch for Geo Guess plugin folder removal\n[Path]\nPathModified=%s\nPathModified=%s\n[Install]\nWantedBy=default.target\n" % (os.path.join(OMARCHY_CONFIG, "plugins"), os.path.join(OMARCHY_CONFIG, "shell.json"))
    before = (read_text(service), read_text(path_unit))
    if not (write_owned(service, service_body) and write_owned(path_unit, path_body)): return
    if (read_text(service), read_text(path_unit)) == before: return
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", UNIT + ".path"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError: pass


def remove_watch():
    service, path_unit = os.path.join(unit_dir(), UNIT + ".service"), os.path.join(unit_dir(), UNIT + ".path")
    if not ((not os.path.lexists(service) or we_own(service)) and (not os.path.lexists(path_unit) or we_own(path_unit))): return
    try:
        subprocess.run(["systemctl", "--user", "disable", "--now", UNIT + ".path", UNIT + ".service"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError: pass
    remove_owned(service); remove_owned(path_unit)


def install_copy():
    src = os.path.join(PLUGIN_DIR, "uninstall.py")
    if not regular(src): src = os.path.abspath(__file__)
    if not regular(src): return False
    content = read_text(src)
    if content is None or not content.startswith("#!/usr/bin/env python3"): return False
    existing = read_text(UNINSTALL_DST)
    if os.path.lexists(OWNER_RECORD) and not regular(OWNER_RECORD): return False
    if os.path.lexists(UNINSTALL_DST):
        if not regular(UNINSTALL_DST) or read_text(OWNER_RECORD) != owner_record(existing or ""): return False
    elif os.path.lexists(OWNER_RECORD):
        return False
    if existing != content and not atomic_write(UNINSTALL_DST, content, 0o755): return False
    return atomic_write(OWNER_RECORD, owner_record(content), 0o600)


def remove_copy():
    content = read_text(UNINSTALL_DST)
    record = read_text(OWNER_RECORD)
    if content is None or record != owner_record(content): return
    try: os.remove(UNINSTALL_DST); os.remove(OWNER_RECORD)
    except FileNotFoundError: pass


def light_clean(): rewrite_flags(remove=True); remove_hosts()
def full_clean(): light_clean(); remove_watch(); remove_copy()
def cmd_setup():
    if not install_copy(): print("Geo Guess refused to replace an unowned uninstall script", file=sys.stderr); return 1
    install_watch(); rewrite_flags(add=True); print("ok"); return 0
def cmd_disable():
    if "--unless-enabled" in sys.argv and plugin_is_enabled_in_shell_config(): print("skip"); return 0
    light_clean(); print("ok"); return 0
def cmd_remove():
    if "--remove-if-missing" in sys.argv and os.path.isdir(PLUGIN_DIR): print("skip"); return 0
    if "--unless-enabled" in sys.argv and plugin_is_enabled_in_shell_config(): print("skip"); return 0
    full_clean(); print("ok"); return 0
def cmd_sync():
    if not os.path.isdir(PLUGIN_DIR): full_clean(); print("ok"); return 0
    if plugin_is_enabled_in_shell_config(): rewrite_flags(add=True); print("enabled"); return 0
    light_clean(); print("disabled"); return 0

def cmd_install_host():
    host_bin = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PLUGIN_DIR, "guess-host")
    if not install_hosts(host_bin):
        return 1
    print("Registered com.lessunderrated.geoguess")
    return 0


def cmd_remove_host():
    if remove_hosts():
        print("Removed owned Geo Guess native-messaging host")
    else:
        print("No owned Geo Guess native-messaging host files found")
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ["setup"]: return cmd_setup()
    if args[:1] == ["install-host"]: return cmd_install_host()
    if args[:1] == ["remove-host"]: return cmd_remove_host()
    if "--sync" in args: return cmd_sync()
    if "--remove" in args or "--remove-if-missing" in args: return cmd_remove()
    if not os.path.isdir(PLUGIN_DIR): return cmd_remove()
    return cmd_disable()

if __name__ == "__main__": sys.exit(main())
