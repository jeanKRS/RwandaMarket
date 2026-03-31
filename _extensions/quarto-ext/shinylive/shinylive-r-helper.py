#!/usr/bin/env python3
"""
Helper script that provides R (webR) language resources using the Python
shinylive package's shared assets directory.

This bridges the gap when the R shinylive package is not installed but
the Python shinylive package is available, since both share the same
shinylive web assets (including webR files).

Usage:
  python3 shinylive-r-helper.py extension info
  python3 shinylive-r-helper.py extension base-htmldeps --sw-dir <dir>
  python3 shinylive-r-helper.py extension language-resources
  python3 shinylive-r-helper.py extension app-resources < app.json
"""

import json
import os
import sys


def get_assets_dir():
    """Get shinylive assets directory from the Python shinylive package."""
    from shinylive._assets import shinylive_assets_dir
    return shinylive_assets_dir()


def get_assets_version():
    """Get the shinylive assets version."""
    assets_dir = get_assets_dir()
    # The directory name is like shinylive-0.10.8
    return os.path.basename(assets_dir).replace("shinylive-", "")


def cmd_info():
    """Return extension info (version, assets_version, scripts)."""
    assets_dir = get_assets_dir()
    assets_version = get_assets_version()
    codeblock_script = os.path.join(assets_dir, "scripts", "codeblock-to-json.js")
    return {
        "version": assets_version,
        "assets_version": assets_version,
        "scripts": {
            "codeblock-to-json": codeblock_script
        }
    }


def cmd_base_htmldeps(sw_dir):
    """Return base HTML dependencies (service worker + core shinylive assets).

    Delegates to the Python shinylive CLI since these are language-agnostic.
    """
    import subprocess
    result = subprocess.run(
        ["shinylive", "extension", "base-htmldeps", "--sw-dir", sw_dir],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)


def cmd_language_resources():
    """Return R-specific (webR) resource files from the shared assets."""
    assets_dir = get_assets_dir()
    shinylive_dir = os.path.join(assets_dir, "shinylive")
    webr_dir = os.path.join(shinylive_dir, "webr")

    resources = []
    if os.path.isdir(webr_dir):
        for root, _dirs, files in os.walk(webr_dir):
            for filename in sorted(files):
                full_path = os.path.join(root, filename)
                rel_path = "shinylive/" + os.path.relpath(full_path, shinylive_dir)
                resources.append({
                    "name": rel_path,
                    "path": full_path
                })

    # Also include R package resources if available
    packages_dir = os.path.join(shinylive_dir, "webr", "packages")
    # packages are already included via the webr walk above

    return resources


def cmd_app_resources():
    """Return app-specific resources. For R, this is typically empty."""
    # Read app JSON from stdin (as the Lua filter pipes it)
    _app_json = sys.stdin.read()
    # R shinylive doesn't return app-specific resources
    return []


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: shinylive-r-helper.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if args[0] == "--version":
        print(get_assets_version())
        return

    if args[0] != "extension" or len(args) < 2:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)

    subcmd = args[1]

    if subcmd == "info":
        result = cmd_info()
    elif subcmd == "base-htmldeps":
        sw_dir = "."
        if "--sw-dir" in args:
            idx = args.index("--sw-dir")
            if idx + 1 < len(args):
                sw_dir = args[idx + 1]
        result = cmd_base_htmldeps(sw_dir)
    elif subcmd == "language-resources":
        result = cmd_language_resources()
    elif subcmd == "app-resources":
        result = cmd_app_resources()
    else:
        print(f"Unknown extension subcommand: {subcmd}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
