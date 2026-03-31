"""
End-to-end tests for shinylive-r rendering in the browser.

Uses a simple HTTP server and validates that the rendered HTML
has the correct structure for shinylive to initialize webR-based
Shiny apps in the browser.
"""

import http.server
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DOCS_DIR = PROJECT_DIR / "docs"


class SimpleServer:
    """A simple HTTP server for testing."""

    def __init__(self, directory, port=0):
        self.directory = directory
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
            *args, directory=str(directory), **kwargs
        )
        self.server = http.server.HTTPServer(("127.0.0.1", port), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"


class TestShinyliveE2E(unittest.TestCase):
    """End-to-end tests verifying the shinylive output works correctly."""

    @classmethod
    def setUpClass(cls):
        """Ensure the page is rendered and start an HTTP server."""
        # Render if needed
        output_file = DOCS_DIR / "sample_shiny_page.html"
        if not output_file.exists():
            env = os.environ.copy()
            env["RENV_CONFIG_AUTOLOADER_ENABLED"] = "FALSE"
            subprocess.run(
                ["quarto", "render", "sample_shiny_page.qmd"],
                cwd=str(PROJECT_DIR), env=env, timeout=300
            )

        cls.server = SimpleServer(DOCS_DIR)
        cls.server.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def fetch(self, path):
        """Fetch a URL from the test server."""
        url = f"{self.server.base_url}/{path}"
        with urllib.request.urlopen(url) as resp:
            return resp.read().decode("utf-8"), resp.status

    def fetch_status(self, path):
        """Get HTTP status code for a path."""
        url = f"{self.server.base_url}/{path}"
        try:
            with urllib.request.urlopen(url) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_page_loads(self):
        """The sample shiny page should load successfully."""
        content, status = self.fetch("sample_shiny_page.html")
        self.assertEqual(status, 200)
        self.assertIn("<!DOCTYPE html>", content)

    def test_shinylive_blocks_present(self):
        """The page should contain shinylive-r code blocks."""
        content, _ = self.fetch("sample_shiny_page.html")
        blocks = re.findall(r'<pre class="shinylive-r"', content)
        self.assertEqual(len(blocks), 2, "Expected 2 shinylive-r blocks")

    def test_shinylive_js_loadable(self):
        """The shinylive JavaScript bundle should be loadable."""
        content, _ = self.fetch("sample_shiny_page.html")
        # Extract the JS path
        match = re.search(r'src="([^"]*run-python-blocks\.js)"', content)
        self.assertIsNotNone(match, "run-python-blocks.js script tag not found")
        js_path = match.group(1)
        status = self.fetch_status(js_path)
        self.assertEqual(status, 200, f"Failed to load {js_path}")

    def test_shinylive_css_loadable(self):
        """The shinylive CSS should be loadable."""
        content, _ = self.fetch("sample_shiny_page.html")
        match = re.search(r'href="([^"]*shinylive\.css)"', content)
        self.assertIsNotNone(match, "shinylive.css link tag not found")
        css_path = match.group(1)
        status = self.fetch_status(css_path)
        self.assertEqual(status, 200, f"Failed to load {css_path}")

    def test_service_worker_loadable(self):
        """The service worker script should be accessible."""
        status = self.fetch_status("shinylive-sw.js")
        self.assertEqual(status, 200, "shinylive-sw.js not accessible")

    def test_webr_wasm_loadable(self):
        """The webR WASM binary should be accessible."""
        content, _ = self.fetch("sample_shiny_page.html")
        match = re.search(r'src="([^"]*shinylive-[\d.]+)/shinylive/', content)
        self.assertIsNotNone(match, "Could not find shinylive version dir")
        version_dir = match.group(1)
        wasm_path = f"{version_dir}/shinylive/webr/R.wasm"
        status = self.fetch_status(wasm_path)
        self.assertEqual(status, 200, f"R.wasm not accessible at {wasm_path}")

    def test_webr_js_loadable(self):
        """The webR JavaScript should be accessible."""
        content, _ = self.fetch("sample_shiny_page.html")
        match = re.search(r'src="([^"]*shinylive-[\d.]+)/shinylive/', content)
        self.assertIsNotNone(match)
        version_dir = match.group(1)
        js_path = f"{version_dir}/shinylive/webr/R.js"
        status = self.fetch_status(js_path)
        self.assertEqual(status, 200, f"R.js not accessible at {js_path}")

    def test_shinylive_js_detects_r_blocks(self):
        """The run-python-blocks.js should contain R block detection logic."""
        content, _ = self.fetch("sample_shiny_page.html")
        match = re.search(r'src="([^"]*run-python-blocks\.js)"', content)
        js_content, _ = self.fetch(match.group(1))
        self.assertIn(".shinylive-r", js_content)
        self.assertIn('"r"', js_content)

    def test_load_shinylive_sw_handles_localhost(self):
        """The service worker loader should work on localhost."""
        content, _ = self.fetch("sample_shiny_page.html")
        match = re.search(r'src="([^"]*load-shinylive-sw\.js)"', content)
        self.assertIsNotNone(match)
        sw_content, _ = self.fetch(match.group(1))
        self.assertIn("localhost", sw_content)
        self.assertIn("127.0.0.1", sw_content)

    def test_no_stale_old_assets(self):
        """There should be no leftover old shinylive asset directories."""
        site_libs = DOCS_DIR / "site_libs" / "quarto-contrib"
        if site_libs.exists():
            shinylive_dirs = [
                d.name for d in site_libs.iterdir()
                if d.is_dir() and d.name.startswith("shinylive-") and d.name != "shinylive-quarto-css"
            ]
            self.assertEqual(
                len(shinylive_dirs), 1,
                f"Expected exactly one shinylive version directory, found: {shinylive_dirs}"
            )


if __name__ == "__main__":
    unittest.main()
