#!/usr/bin/env python3
"""Content-aware native-messaging host install and remove."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UNINSTALL = os.path.join(REPO, "uninstall.py")
INSTALL_SH = os.path.join(REPO, "scripts", "install-guess-host.sh")
UNINSTALL_SH = os.path.join(REPO, "scripts", "uninstall-guess-host.sh")
HOST_BIN = os.path.join(REPO, "guess-host")
HOST_NAME = "com.lessunderrated.geoguess.json"
MARKER_HOST = """{
  "x-omarchy-owner": "lessunderrated.geoguess",
  "name": "com.lessunderrated.geoguess",
  "description": "user changed this host",
  "path": "/tmp/not-geoguess",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"]
}
"""


class HostOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="geoguess-host-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.config = os.path.join(self.home, ".config")
        self.host_files = (
            os.path.join(self.config, "chromium", "NativeMessagingHosts", HOST_NAME),
            os.path.join(self.config, "chromium", "Default", "NativeMessagingHosts", HOST_NAME),
        )

    def run_py(self, *args):
        env = os.environ.copy()
        env["HOME"] = self.home
        env.pop("XDG_CONFIG_HOME", None)
        return subprocess.run(
            [sys.executable, UNINSTALL, *args],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )

    def run_sh(self, script):
        env = os.environ.copy()
        env["HOME"] = self.home
        env.pop("XDG_CONFIG_HOME", None)
        return subprocess.run(
            ["bash", script],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )

    def read(self, path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_install_writes_digest_and_can_run_twice(self):
        first = self.run_py("install-host", HOST_BIN)
        self.assertEqual(first.returncode, 0, first.stderr)
        for path in self.host_files:
            data = json.loads(self.read(path))
            self.assertIn("x-omarchy-sha256", data)
            self.assertEqual(data["path"], HOST_BIN)
        second = self.run_py("install-host", HOST_BIN)
        self.assertEqual(second.returncode, 0, second.stderr)

    def test_install_refuses_user_edited_file_that_keeps_owner_marker(self):
        path = self.host_files[0]
        self.write(path, MARKER_HOST)
        result = self.run_py("install-host", HOST_BIN)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unowned host file", result.stderr)
        self.assertEqual(self.read(path), MARKER_HOST)

    def test_install_refuses_edited_payload_even_with_matching_digest(self):
        path = self.host_files[0]
        payload = {
            "allowed_origins": ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"],
            "description": "user changed this host",
            "name": "com.lessunderrated.geoguess",
            "path": HOST_BIN,
            "type": "stdio",
            "x-omarchy-owner": "lessunderrated.geoguess",
        }
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload["x-omarchy-sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        edited = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self.write(path, edited)
        result = self.run_py("install-host", HOST_BIN)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read(path), edited)

    def test_remove_leaves_user_edited_marked_file(self):
        self.assertEqual(self.run_py("install-host", HOST_BIN).returncode, 0)
        path = self.host_files[0]
        self.write(path, MARKER_HOST)
        result = self.run_py("remove-host")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.read(path), MARKER_HOST)

    def test_remove_deletes_owned_host(self):
        self.assertEqual(self.run_py("install-host", HOST_BIN).returncode, 0)
        result = self.run_py("remove-host")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in self.host_files:
            self.assertFalse(os.path.lexists(path))

    def test_legacy_exact_file_is_still_owned(self):
        path = self.host_files[0]
        plugin_host = os.path.join(self.config, "omarchy", "plugins", "lessunderrated.geoguess", "guess-host")
        os.makedirs(os.path.dirname(plugin_host), exist_ok=True)
        shutil.copy2(HOST_BIN, plugin_host)
        os.chmod(plugin_host, 0o755)
        legacy = {
            "allowed_origins": ["chrome-extension://ghhlkacefalngacompmfpiekbmblamgg/"],
            "description": "Geo Guess next-round helper",
            "name": "com.lessunderrated.geoguess",
            "path": plugin_host,
            "type": "stdio",
            "x-omarchy-owner": "lessunderrated.geoguess",
        }
        self.write(path, json.dumps(legacy, indent=2) + "\n")
        result = self.run_py("install-host", HOST_BIN)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.read(path))
        self.assertIn("x-omarchy-sha256", data)
        self.assertEqual(data["path"], HOST_BIN)

    def test_disable_does_not_delete_user_edited_host(self):
        path = self.host_files[0]
        self.write(path, MARKER_HOST)
        plugin_dir = os.path.join(self.config, "omarchy", "plugins", "lessunderrated.geoguess")
        os.makedirs(plugin_dir, exist_ok=True)
        shutil.copy2(UNINSTALL, os.path.join(plugin_dir, "uninstall.py"))
        result = self.run_py("--disable")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read(path), MARKER_HOST)

    def test_shell_wrappers_use_content_digest(self):
        first = self.run_sh(INSTALL_SH)
        self.assertEqual(first.returncode, 0, first.stderr)
        path = self.host_files[0]
        self.write(path, MARKER_HOST)
        refused = self.run_sh(INSTALL_SH)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(self.read(path), MARKER_HOST)
        leftover = self.run_sh(UNINSTALL_SH)
        self.assertEqual(leftover.returncode, 0, leftover.stderr)
        self.assertEqual(self.read(path), MARKER_HOST)


if __name__ == "__main__":
    unittest.main()
