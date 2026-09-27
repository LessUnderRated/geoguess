#!/usr/bin/env python3
"""Regression tests for bounded HTTP and native-messaging reads."""
import importlib.machinery
import importlib.util
import json
import os
import struct
import subprocess
import sys
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


lookup = load_module("streetview_lookup", "streetview-lookup")


class FakeHeaders(dict):
    def get(self, key, default=None):
        for current, value in self.items():
            if current.lower() == key.lower():
                return value
        return default


class FakeResponse:
    def __init__(self, body, headers=None):
        self.body = body
        self.headers = FakeHeaders(headers or {})
        self.offset = 0
        self.read_calls = 0

    def read(self, size=-1):
        self.read_calls += 1
        if size is None or size < 0:
            chunk = self.body[self.offset:]
            self.offset = len(self.body)
            return chunk
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class BoundedHttpTests(unittest.TestCase):
    def test_reads_body_under_limit(self):
        response = FakeResponse(b'{"ok":true}')
        with mock.patch("urllib.request.urlopen", return_value=response):
            text = lookup.read_http_text(urllib.request.Request("http://example.test/"))
        self.assertEqual(text, '{"ok":true}')

    def test_rejects_body_over_limit_without_keeping_it(self):
        oversized = b"x" * (lookup.MAX_HTTP_BYTES + 1)
        response = FakeResponse(oversized)
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(lookup.ResponseTooLarge):
                lookup.read_http_text(urllib.request.Request("http://example.test/"))
        self.assertGreater(response.read_calls, 0)
        self.assertLessEqual(response.offset, lookup.MAX_HTTP_BYTES + lookup._HTTP_CHUNK)

    def test_rejects_content_length_before_reading_body(self):
        response = FakeResponse(b"never-read", headers={"Content-Length": str(lookup.MAX_HTTP_BYTES + 1)})
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(lookup.ResponseTooLarge):
                lookup.read_http_text(urllib.request.Request("http://example.test/"))
        self.assertEqual(response.read_calls, 0)

    def test_find_place_returns_none_on_oversized_search_page(self):
        response = FakeResponse(b"x" * (lookup.MAX_HTTP_BYTES + 50))
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(lookup.find_place("Paris", 48.8, 2.3))

    def test_place_photo_returns_none_on_oversized_body(self):
        response = FakeResponse(b"x" * (lookup.MAX_HTTP_BYTES + 50))
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(lookup.place_photo("0x1:0x2"))

    def test_official_panos_dies_on_oversized_tile(self):
        response = FakeResponse(b"x" * (lookup.MAX_HTTP_BYTES + 50))
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(SystemExit):
                lookup.official_panos(1, 2)

    def test_nearest_panorama_dies_on_oversized_search(self):
        response = FakeResponse(b"x" * (lookup.MAX_HTTP_BYTES + 50))
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(SystemExit):
                lookup.nearest_panorama(40.7, -74.0)


class NativeHostBoundsTests(unittest.TestCase):
    def test_huge_native_length_does_not_allocate_the_claimed_body(self):
        payload = struct.pack("<I", 3_000_000_000)
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "guess-host")],
            input=payload,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertGreaterEqual(len(proc.stdout), 4)
        size = struct.unpack("<I", proc.stdout[:4])[0]
        body = json.loads(proc.stdout[4:4 + size])
        self.assertEqual(body.get("ok"), False)


if __name__ == "__main__":
    unittest.main()
