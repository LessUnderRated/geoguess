#!/usr/bin/env python3
"""Command-injection and shared-file rewrite regressions."""
import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import urllib.request
from unittest import mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_module(name, filename):
    path = os.path.join(REPO, filename)
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


lookup = load_module("streetview_lookup_safety", "streetview-lookup")
host = load_module("guess_host_safety", "guess-host")


class PanoidSafetyTests(unittest.TestCase):
    def test_rejects_apostrophe_and_shell_metacharacters(self):
        self.assertIsNone(lookup.safe_panoid("abc'def"))
        self.assertIsNone(lookup.safe_panoid("abc;id"))
        self.assertIsNone(lookup.safe_panoid("abc$(id)"))
        self.assertIsNone(lookup.safe_panoid(""))
        self.assertEqual(lookup.safe_panoid("TGJCy3uY7E1bnMYA2ykgZQ"), "TGJCy3uY7E1bnMYA2ykgZQ")
        self.assertEqual(lookup.permalink("abc'def", 1.0, 2.0), "")

    def test_nearest_panorama_drops_unsafe_id_from_google(self):
        body = b'[[1],[2,"abc\'evil"],[null,null,40.7,-74.0]]'
        response = mock.MagicMock()
        response.headers = {"Content-Length": str(len(body))}
        response.read.side_effect = [body, b""]
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(lookup.nearest_panorama(40.7, -74.0))


class MapsUrlSafetyTests(unittest.TestCase):
    def test_lookup_and_host_share_the_maps_allowlist(self):
        good = (
            "https://www.google.com/maps/@40.7,-74.0,3a,75y,0h,90t"
            "/data=!3m4!1e1!3m2!1sTGJCy3uY7E1bnMYA2ykgZQ!2e2"
        )
        self.assertEqual(lookup.safe_maps_url(good), good)
        self.assertEqual(host.safe_maps_url(good), good)
        self.assertEqual(lookup.safe_maps_url(good + "#geoguess"), good)
        for bad in (
            "javascript:alert(1)",
            "http://www.google.com/maps/@1,2",
            "https://evil.example/maps/@1,2",
            "https://www.google.com.evil/maps/@1,2",
            "https://www.google.com/maps/@1,2;id",
            "https://www.google.com/maps/@1,2$(id)",
            "https://www.google.com/maps/@1,2`id`",
            "",
        ):
            self.assertEqual(lookup.safe_maps_url(bad), "")
            self.assertEqual(host.safe_maps_url(bad), "")

    def test_permalink_output_is_a_maps_url(self):
        url = lookup.permalink("TGJCy3uY7E1bnMYA2ykgZQ", 40.7, -74.0)
        self.assertEqual(lookup.safe_maps_url(url), url)


class CappedStdoutTests(unittest.TestCase):
    def test_drops_output_over_the_limit_without_returning_it(self):
        raw = host.capped_stdout(
            [sys.executable, "-c", "import sys; sys.stdout.write('x' * 200000)"],
            timeout=5,
            limit=64 * 1024,
        )
        self.assertIsNone(raw)

    def test_keeps_small_output(self):
        raw = host.capped_stdout(
            [sys.executable, "-c", "import sys; sys.stdout.write('ok')"],
            timeout=5,
            limit=64 * 1024,
        )
        self.assertEqual(raw, b"ok")


class FlagRewriteTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="geoguess-flags-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        os.environ["HOME"] = self.home
        os.environ.pop("XDG_CONFIG_HOME", None)
        self.uninst = load_module("uninstall_flags_" + os.path.basename(self.home), "uninstall.py")
        os.makedirs(self.uninst.EXTENSION_DIR, exist_ok=True)
        self.flags = self.uninst.FLAG_FILES[0]
        os.makedirs(os.path.dirname(self.flags), exist_ok=True)

    def test_add_appends_to_the_existing_load_extension_line(self):
        with open(self.flags, "w", encoding="utf-8") as fh:
            fh.write("--load-extension=/home/user/other-ext\n--force-dark-mode\n")
        self.uninst.rewrite_flags(add=True)
        with open(self.flags, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(
            text,
            "--load-extension=/home/user/other-ext," + self.uninst.EXTENSION_DIR + "\n--force-dark-mode\n",
        )
        self.assertEqual(text.count("--load-extension="), 1)

    def test_remove_strips_only_this_plugin_path(self):
        with open(self.flags, "w", encoding="utf-8") as fh:
            fh.write(
                "--load-extension=/home/user/other-ext,"
                + self.uninst.EXTENSION_DIR
                + "\n--force-dark-mode\n"
            )
        self.uninst.rewrite_flags(remove=True)
        with open(self.flags, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text, "--load-extension=/home/user/other-ext\n--force-dark-mode\n")

    def test_add_skips_write_when_result_would_exceed_limit(self):
        padding = "x" * (self.uninst.MAX_CONFIG_BYTES - 80)
        original = "--load-extension=/home/user/other-ext\n#" + padding + "\n"
        with open(self.flags, "w", encoding="utf-8") as fh:
            fh.write(original)
        self.uninst.rewrite_flags(add=True)
        with open(self.flags, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)

    def test_skips_oversized_flags_file(self):
        original = "--force-dark-mode\n" + ("x" * (self.uninst.MAX_CONFIG_BYTES + 50))
        with open(self.flags, "w", encoding="utf-8") as fh:
            fh.write(original)
        self.uninst.rewrite_flags(add=True)
        with open(self.flags, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)


if __name__ == "__main__":
    unittest.main()
