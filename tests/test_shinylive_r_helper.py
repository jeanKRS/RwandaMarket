"""
Unit tests for the shinylive-r-helper.py script.

Tests that the Python-based R shinylive helper correctly provides
webR asset information when the R shinylive package is not installed.
"""

import json
import os
import subprocess
import sys
import unittest

HELPER_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "_extensions", "quarto-ext", "shinylive", "shinylive-r-helper.py"
)


class TestHelperInfo(unittest.TestCase):
    """Test the 'extension info' subcommand."""

    def test_info_returns_valid_json(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "info"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("version", data)
        self.assertIn("assets_version", data)
        self.assertIn("scripts", data)

    def test_info_contains_codeblock_script(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "info"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        self.assertIn("codeblock-to-json", data["scripts"])
        script_path = data["scripts"]["codeblock-to-json"]
        self.assertTrue(
            os.path.exists(script_path),
            f"codeblock-to-json script not found at: {script_path}"
        )

    def test_info_version_format(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "info"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        version = data["assets_version"]
        parts = version.split(".")
        self.assertGreaterEqual(len(parts), 2, f"Invalid version format: {version}")
        for part in parts:
            self.assertTrue(part.isdigit(), f"Non-numeric version part: {part}")


class TestHelperBaseHtmlDeps(unittest.TestCase):
    """Test the 'extension base-htmldeps' subcommand."""

    def test_base_htmldeps_returns_array(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "base-htmldeps", "--sw-dir", "."],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_base_htmldeps_contains_serviceworker(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "base-htmldeps", "--sw-dir", "."],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        sw_deps = [d for d in data if d.get("name") == "shinylive-serviceworker"]
        self.assertEqual(len(sw_deps), 1, "Expected exactly one serviceworker dependency")

    def test_base_htmldeps_contains_shinylive(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "base-htmldeps", "--sw-dir", "."],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        sl_deps = [d for d in data if d.get("name") == "shinylive"]
        self.assertEqual(len(sl_deps), 1, "Expected exactly one shinylive dependency")
        sl = sl_deps[0]
        self.assertIn("scripts", sl)
        self.assertIn("stylesheets", sl)


class TestHelperLanguageResources(unittest.TestCase):
    """Test the 'extension language-resources' subcommand."""

    def test_language_resources_returns_webr_files(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "language-resources"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Expected webR resource files")

    def test_language_resources_contain_r_wasm(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "language-resources"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        wasm_files = [d for d in data if d["name"].endswith(".wasm")]
        self.assertGreater(len(wasm_files), 0, "Expected at least one .wasm file for webR")

    def test_language_resources_contain_webr_worker(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "language-resources"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        worker_files = [d for d in data if "webr-worker" in d["name"]]
        self.assertGreater(len(worker_files), 0, "Expected webr-worker.js in resources")

    def test_language_resources_paths_exist(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "language-resources"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        for resource in data[:10]:
            self.assertTrue(
                os.path.exists(resource["path"]),
                f"Resource file not found: {resource['path']}"
            )

    def test_language_resources_names_start_with_shinylive(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "language-resources"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        for resource in data:
            self.assertTrue(
                resource["name"].startswith("shinylive/webr/"),
                f"Expected resource name to start with 'shinylive/webr/', got: {resource['name']}"
            )


class TestHelperAppResources(unittest.TestCase):
    """Test the 'extension app-resources' subcommand."""

    def test_app_resources_returns_empty_array(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "extension", "app-resources"],
            capture_output=True, text=True, input='[{"name":"app.R","content":"library(shiny)"}]'
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)


class TestHelperErrorHandling(unittest.TestCase):
    """Test error handling for invalid commands."""

    def test_unknown_command_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "unknown"],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_no_args_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, HELPER_SCRIPT, "--version"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        version = result.stdout.strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
