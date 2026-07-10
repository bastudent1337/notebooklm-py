"""Unit tests for the ``.claude-plugin/`` Claude Code plugin manifest.

Lives at the tests root (like ``test_mcp_desktop_extension.py``) because it
imports nothing from ``fastmcp`` — these are static JSON assertions, so they
run unconditionally even without the ``mcp`` extra installed.

Two files are validated:

* ``marketplace.json`` — lets ``/plugin marketplace add <owner>/notebooklm-py``
  discover this repo as a plugin source.
* ``plugin.json`` — the plugin itself: metadata plus an inline ``mcpServers``
  block that launches the same server the CLI's ``notebooklm mcp install``
  and the ``.mcpb`` desktop bundle both use.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PLUGIN_DIR = _REPO_ROOT / ".claude-plugin"
_MARKETPLACE = _PLUGIN_DIR / "marketplace.json"
_PLUGIN_MANIFEST = _PLUGIN_DIR / "plugin.json"


def _pyproject_version() -> str:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - exercised on Python <3.11
        import tomli as tomllib

    pyproject = _REPO_ROOT / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


# --------------------------------------------------------------------------- #
# marketplace.json
# --------------------------------------------------------------------------- #


def test_marketplace_is_valid_json_with_required_keys() -> None:
    data = json.loads(_MARKETPLACE.read_text(encoding="utf-8"))

    for key in ("name", "owner", "plugins"):
        assert key in data, f"marketplace.json missing required key: {key!r}"

    assert data["owner"]["name"], "marketplace owner.name is required"
    assert isinstance(data["plugins"], list) and data["plugins"], (
        "marketplace.json plugins must be a non-empty list"
    )


def test_marketplace_plugin_entry_points_at_repo_root() -> None:
    """The plugin lives in this same repo (no subdirectory), so its ``source``
    must be ``"./"`` relative to the marketplace root."""
    data = json.loads(_MARKETPLACE.read_text(encoding="utf-8"))
    entry = data["plugins"][0]
    assert entry["name"] == "notebooklm-mcp"
    assert entry["source"] == "./"


# --------------------------------------------------------------------------- #
# plugin.json
# --------------------------------------------------------------------------- #


def test_plugin_manifest_is_valid_json_with_required_keys() -> None:
    data = json.loads(_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    for key in ("name", "version", "description", "mcpServers"):
        assert key in data, f"plugin.json missing required key: {key!r}"
    assert data["name"] == "notebooklm-mcp"


def test_plugin_manifest_mcp_server_matches_cli_install_block() -> None:
    """The inline ``mcpServers`` block must launch the server the same way
    ``notebooklm mcp install`` and the ``.mcpb`` bundle do (via ``uvx``, no
    global install required)."""
    from notebooklm._app.mcp_install import build_server_block

    data = json.loads(_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    assert "notebooklm" in servers
    assert servers["notebooklm"] == build_server_block()


def test_plugin_manifest_version_matches_package_version() -> None:
    """Keeps ``plugin.json`` from silently drifting from ``pyproject.toml``,
    mirroring ``test_manifest_version_matches_package_version`` for the
    ``.mcpb`` bundle in ``test_mcp_desktop_extension.py``."""
    pyproject_version = _pyproject_version()
    manifest_version = json.loads(_PLUGIN_MANIFEST.read_text(encoding="utf-8"))["version"]
    assert manifest_version == pyproject_version, (
        f".claude-plugin/plugin.json version ({manifest_version!r}) is out of sync "
        f"with pyproject.toml ({pyproject_version!r}); bump both in the same commit."
    )


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
