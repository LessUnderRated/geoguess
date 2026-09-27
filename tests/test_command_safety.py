#!/usr/bin/env python3
"""Command-injection and shared-file rewrite regressions."""
import importlib.machinery
import importlib.util
import os
import shutil
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

    def test_add_does_not_inject_into_other_load_extension_lines(self):
        with open(self.flags, "w", encoding="utf-8") as fh:
            fh.write("--load-extension=/home/user/other-ext\n--force-dark-mode\n")
        self.uninst.rewrite_flags(add=True)
        with open(self.flags, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("--load-extension=/home/user/other-ext\n", text)
        self.assertIn("--load-extension=" + self.uninst.EXTENSION_DIR, text)
        self.assertNotIn("/home/user/other-ext," + self.uninst.EXTENSION_DIR, text)
        self.assertNotIn(self.uninst.EXTENSION_DIR + ",/home/user/other-ext", text)


if __name__ == "__main__":
    unittest.main()
