#!/usr/bin/env python3
"""Regression tests for uninstall.py ownership and setup re-entry."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UNINSTALL_SRC = os.path.join(REPO, "uninstall.py")
PLUGIN_ID = "lessunderrated.geoguess"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class UninstallOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="geoguess-home-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.config = os.path.join(self.home, ".config")
        self.plugin_dir = os.path.join(self.config, "omarchy", "plugins", PLUGIN_ID)
        os.makedirs(self.plugin_dir, exist_ok=True)
        shutil.copy2(UNINSTALL_SRC, os.path.join(self.plugin_dir, "uninstall.py"))
        self.dst = os.path.join(self.config, "omarchy", f"{PLUGIN_ID}.uninstall.py")
        self.owner = self.dst + ".owner"
        self.unit_dir = os.path.join(self.config, "systemd", "user")
        self.service = os.path.join(self.unit_dir, "lessunderrated-geoguess-gone.service")
        self.path_unit = os.path.join(self.unit_dir, "lessunderrated-geoguess-gone.path")

    def run_uninstall(self, *args):
        env = os.environ.copy()
        env["HOME"] = self.home
        env.pop("XDG_CONFIG_HOME", None)
        return subprocess.run(
            [sys.executable, UNINSTALL_SRC, *args],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )

    def read(self, path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_setup_can_run_twice_with_newline_owner_record(self):
        first = self.run_uninstall("setup")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout.strip(), "ok")
        self.assertTrue(os.path.isfile(self.dst))
        self.assertTrue(os.path.isfile(self.owner))
        copied = self.read(self.dst)
        record = self.read(self.owner)
        self.assertTrue(record.endswith("\n"), "owner record must be written with a trailing newline")
        self.assertEqual(record, digest(copied) + "\n")

        second = self.run_uninstall("setup")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout.strip(), "ok")
        self.assertEqual(self.read(self.owner), digest(self.read(self.dst)) + "\n")
        self.assertTrue(os.path.isfile(self.service))
        self.assertTrue(os.path.isfile(self.path_unit))

    def test_setup_refreshes_owned_copy_when_plugin_script_changes(self):
        self.assertEqual(self.run_uninstall("setup").returncode, 0)
        plugin_script = os.path.join(self.plugin_dir, "uninstall.py")
        text = self.read(plugin_script)
        updated = text + "\n# plugin-local marker\n"
        with open(plugin_script, "w", encoding="utf-8") as fh:
            fh.write(updated)
        result = self.run_uninstall("setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read(self.dst), updated)
        self.assertEqual(self.read(self.owner), digest(updated) + "\n")

    def test_setup_refuses_unowned_existing_copy(self):
        os.makedirs(os.path.dirname(self.dst), exist_ok=True)
        with open(self.dst, "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env python3\nprint('user copy')\n")
        result = self.run_uninstall("setup")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unowned uninstall script", result.stderr)
        self.assertEqual(self.read(self.dst), "#!/usr/bin/env python3\nprint('user copy')\n")

    def test_setup_does_not_overwrite_user_edited_unit(self):
        self.assertEqual(self.run_uninstall("setup").returncode, 0)
        original = self.read(self.service)
        edited = original.replace("Finish Geo Guess Chromium cleanup after plugin remove", "user changed this unit")
        self.assertNotEqual(original, edited)
        with open(self.service, "w", encoding="utf-8") as fh:
            fh.write(edited)
        result = self.run_uninstall("setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read(self.service), edited)

    def test_setup_keeps_plugin_files_under_home_config_when_xdg_differs(self):
        xdg = tempfile.mkdtemp(prefix="geoguess-xdg-")
        self.addCleanup(shutil.rmtree, xdg, ignore_errors=True)
        env = os.environ.copy()
        env["HOME"] = self.home
        env["XDG_CONFIG_HOME"] = xdg
        result = subprocess.run(
            [sys.executable, UNINSTALL_SRC, "setup"],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(self.dst))
        self.assertFalse(os.path.lexists(os.path.join(xdg, "omarchy", f"{PLUGIN_ID}.uninstall.py")))
        xdg_service = os.path.join(xdg, "systemd", "user", "lessunderrated-geoguess-gone.service")
        self.assertTrue(os.path.isfile(xdg_service))
        self.assertFalse(os.path.isfile(self.service))

    def test_unless_enabled_skips_when_shell_json_is_oversized(self):
        os.makedirs(os.path.join(self.config, "omarchy"), exist_ok=True)
        shell = os.path.join(self.config, "omarchy", "shell.json")
        with open(shell, "w", encoding="utf-8") as fh:
            fh.write("{" + ("x" * (1024 * 1024 + 10)))
        result = self.run_uninstall("--unless-enabled")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "skip")


if __name__ == "__main__":
    unittest.main()
