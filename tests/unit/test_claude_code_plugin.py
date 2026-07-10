"""Unit tests for the ``.claude-plugin/`` Claude Code plugin manifest.

Lives at the tests root (like ``test_mcp_desktop_extension.py``) because it
imports nothing from ``fastmcp`` — these are static JSON assertions, so they
run unconditionally even without the ``mcp`` extra installed.

Two files are validated:

* ``marketplace.json`` — lets ``/plugin marketplace add <owner>/notebooklm-py``
  discover this repo as a plugin source.
* ``plugin.json`` — the plugin itself: metadata plus an inline ``mcpServers``
  block that launches the same server the CLI's ``notebooklm mcp install``
  and the ``.mcpb`` desktop bundle both use, plus the ``skills`` field that
  points Claude Code at the bundled ``skills/notebooklm/`` Agent Skill.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PLUGIN_DIR = _REPO_ROOT / ".claude-plugin"
_MARKETPLACE = _PLUGIN_DIR / "marketplace.json"
_PLUGIN_MANIFEST = _PLUGIN_DIR / "plugin.json"
_SKILL_DIR = _REPO_ROOT / "skills" / "notebooklm"
_SKILL_MD = _SKILL_DIR / "SKILL.md"


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal flat ``key: value`` frontmatter parser (no YAML dependency).

    Sufficient for this skill's frontmatter shape (single-line ``name:`` /
    ``description:`` pairs, same convention ``_app/skill.py``'s
    ``add_version_comment`` assumes) -- not a general YAML parser.
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


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


def test_plugin_manifest_skills_field_points_at_existing_dir() -> None:
    """``skills`` is what makes this repo's Claude Code plugin auto-load the
    bundled notebooklm Agent Skill; the directory it names must actually
    exist and contain the skill."""
    data = json.loads(_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert data["skills"] == "./skills/"

    skills_dir = _REPO_ROOT / "skills"
    assert skills_dir.is_dir(), f"plugin.json skills dir does not exist: {skills_dir}"
    assert (skills_dir / "notebooklm" / "SKILL.md").is_file()


# --------------------------------------------------------------------------- #
# skills/notebooklm/ (the bundled Agent Skill the plugin's ``skills`` field
# and the wheel's ``notebooklm/data/skill/`` package data both point at)
# --------------------------------------------------------------------------- #


def test_bundled_skill_has_valid_frontmatter() -> None:
    """The bundled skill's ``SKILL.md`` declares the ``name`` / ``description``
    frontmatter Claude Code's skill loader requires."""
    frontmatter = _parse_frontmatter(_SKILL_MD.read_text(encoding="utf-8"))
    assert frontmatter.get("name") == "notebooklm"
    assert frontmatter.get("description"), "SKILL.md frontmatter description must be non-empty"


def test_no_root_skill_md() -> None:
    """Pins the anti-shadowing invariant from the directory refactor.

    A root-level ``SKILL.md`` is treated as a single-skill plugin marker
    (Claude Code v2.1.142+) that SHADOWS the ``skills/`` directory this
    plugin now advertises via ``plugin.json``'s ``skills`` field -- and it
    also wins in ``npx skills`` copy-mode discovery, where the shallower path
    takes precedence. The refactor moved the skill to
    ``skills/notebooklm/SKILL.md``; a root ``SKILL.md`` must never come back.
    """
    assert not (_REPO_ROOT / "SKILL.md").exists()


def test_skill_launcher_is_executable() -> None:
    """``scripts/nlm`` must keep its executable bit in the checkout.

    POSIX-only: Windows has no exec-bit concept, and the packaging/paths this
    guards (a checkout consumed via git or a source distribution) don't apply
    there; ``notebooklm skill install`` separately chmods 0o755 on write to
    compensate for exec bits that don't survive some install paths (e.g. a
    zipped wheel), so a non-executable checkout file would still install fine
    -- this test guards the checkout/packaging source of truth itself.
    """
    if sys.platform == "win32":
        pytest.skip("POSIX executable bit has no meaning on Windows")

    launcher = _SKILL_DIR / "scripts" / "nlm"
    mode = launcher.stat().st_mode
    assert mode & stat.S_IXUSR, f"{launcher} is not executable (mode {oct(mode)})"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
