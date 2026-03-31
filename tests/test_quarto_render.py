"""
Integration tests for Quarto rendering with shinylive-r blocks.

Tests that the modified Lua filter and Python helper correctly render
Quarto documents containing shinylive-r code blocks into HTML with
the proper structure for interactive webR-based Shiny components.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent


class TestQuartoRenderShinyliveR(unittest.TestCase):
    """Integration tests for rendering shinylive-r blocks in Quarto."""

    @classmethod
    def setUpClass(cls):
        """Render the sample shiny page once for all tests."""
        env = os.environ.copy()
        env["RENV_CONFIG_AUTOLOADER_ENABLED"] = "FALSE"
        result = subprocess.run(
            ["quarto", "render", "sample_shiny_page.qmd"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, env=env,
            timeout=300
        )
        cls.render_result = result
        cls.output_file = PROJECT_DIR / "docs" / "sample_shiny_page.html"
        if cls.output_file.exists():
            cls.html_content = cls.output_file.read_text()
        else:
            cls.html_content = ""

    def test_render_succeeds(self):
        """Quarto render should complete (exit 0) and produce output."""
        self.assertEqual(
            self.render_result.returncode, 0,
            f"Render failed.\nstdout: {self.render_result.stdout}\nstderr: {self.render_result.stderr}"
        )
        self.assertTrue(self.output_file.exists(), "Output HTML file not created")

    def test_html_contains_shinylive_r_blocks(self):
        """Rendered HTML should contain shinylive-r pre blocks."""
        self.assertIn('class="shinylive-r"', self.html_content)
        self.assertIn('data-engine="r"', self.html_content)

    def test_html_loads_shinylive_js(self):
        """Rendered HTML should include the shinylive JavaScript assets."""
        self.assertIn("load-shinylive-sw.js", self.html_content)
        self.assertIn("run-python-blocks.js", self.html_content)
        self.assertIn("shinylive.css", self.html_content)

    def test_html_has_serviceworker_meta(self):
        """Rendered HTML should have the service worker meta tag."""
        self.assertIn('name="shinylive:serviceworker_dir"', self.html_content)

    def test_webr_assets_present(self):
        """The webR assets should be in the output directory."""
        # Find the shinylive assets directory
        site_libs = PROJECT_DIR / "docs" / "site_libs" / "quarto-contrib"
        shinylive_dirs = list(site_libs.glob("shinylive-*"))
        self.assertGreater(len(shinylive_dirs), 0, "No shinylive asset directory found")
        shinylive_dir = shinylive_dirs[0]
        webr_dir = shinylive_dir / "shinylive" / "webr"
        self.assertTrue(webr_dir.exists(), f"webR directory not found at {webr_dir}")
        # Check for essential webR files
        essential_files = ["R.wasm", "R.js", "webr-worker.js"]
        for f in essential_files:
            # Some might be nested
            matches = list(webr_dir.rglob(f))
            self.assertGreater(
                len(matches), 0,
                f"Essential webR file '{f}' not found in {webr_dir}"
            )

    def test_shinylive_sw_js_present(self):
        """The shinylive service worker should be in the docs root."""
        sw_file = PROJECT_DIR / "docs" / "shinylive-sw.js"
        self.assertTrue(sw_file.exists(), "shinylive-sw.js not found in docs/")
        content = sw_file.read_text()
        self.assertIn("Shinylive", content)

    def test_html_contains_shiny_app_code(self):
        """The rendered HTML should contain the Shiny app code."""
        self.assertIn("shinyApp(ui, server)", self.html_content)
        self.assertIn("selectInput", self.html_content)
        self.assertIn("sliderInput", self.html_content)

    def test_assets_version_consistency(self):
        """All shinylive assets should use the same version."""
        site_libs = PROJECT_DIR / "docs" / "site_libs" / "quarto-contrib"
        shinylive_dirs = list(site_libs.glob("shinylive-*"))
        # Should have exactly one shinylive version directory (excluding css)
        versioned_dirs = [d for d in shinylive_dirs if d.name != "shinylive-quarto-css"]
        self.assertEqual(
            len(versioned_dirs), 1,
            f"Expected exactly one shinylive version directory, found: {[d.name for d in versioned_dirs]}"
        )


class TestMinimalShinyliveR(unittest.TestCase):
    """Test rendering a minimal shinylive-r document."""

    def test_minimal_r_app_renders(self):
        """A minimal standalone shinylive-r block should render correctly."""
        qmd_content = """---
title: "Test"
format: html
filters:
  - shinylive
---

```{shinylive-r}
#| standalone: true
#| viewerHeight: 200

library(shiny)

ui <- fluidPage(
  textInput("name", "Your name:"),
  textOutput("greeting")
)

server <- function(input, output, session) {
  output$greeting <- renderText({
    paste("Hello,", input$name)
  })
}

shinyApp(ui, server)
```
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy necessary extension files
            ext_src = PROJECT_DIR / "_extensions"
            ext_dst = Path(tmpdir) / "_extensions"
            subprocess.run(["cp", "-r", str(ext_src), str(ext_dst)], check=True)

            # Create _quarto.yml
            quarto_yml = Path(tmpdir) / "_quarto.yml"
            quarto_yml.write_text("project:\n  type: website\n  output-dir: _site\n  resources:\n  - shinylive-sw.js\n")

            # Write QMD file
            qmd_file = Path(tmpdir) / "test.qmd"
            qmd_file.write_text(qmd_content)

            env = os.environ.copy()
            env["RENV_CONFIG_AUTOLOADER_ENABLED"] = "FALSE"

            result = subprocess.run(
                ["quarto", "render", "test.qmd"],
                cwd=tmpdir, capture_output=True, text=True, env=env,
                timeout=300
            )

            self.assertEqual(
                result.returncode, 0,
                f"Minimal render failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )

            output_html = Path(tmpdir) / "_site" / "test.html"
            self.assertTrue(output_html.exists())
            content = output_html.read_text()
            self.assertIn('class="shinylive-r"', content)
            self.assertIn("shinyApp(ui, server)", content)


if __name__ == "__main__":
    unittest.main()
