"""Locate (or create) the player's module library.

A library is any folder the player owns that holds their built modules as a local
Claude Code marketplace:

  <library>/.claude-plugin/marketplace.json
  <library>/plugins/<module-id>/        (module plugins)
  <library>/staging/<module-id>/        (PDF extraction + SURVEY/BUILD-STATE, gitignored)

The forge never writes inside its own plugin folder: when installed from a marketplace
that folder is Claude Code's plugin cache and is replaced on every update.

Discovery order:
  1. SOLO_RPG_LIBRARY (the library folder, or its plugins/ folder)
  2. `library:` in the campaign's solo-rpg.yaml (relative to the vault root)
  3. the nearest folder at or above the working directory with .claude-plugin/marketplace.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # callers report the missing dependency
    yaml = None

FORGE_ROOT = Path(__file__).resolve().parents[1]
MARKET_FILE = Path(".claude-plugin") / "marketplace.json"
CAMPAIGN_FILE = "solo-rpg.yaml"
DEFAULT_NAME = "solo-rpg-library"
CORE_MARKET = "solo-rpg-workshop"  # the marketplace that ships solo-rpg-core and solo-rpg-forge


def _normalise(p: Path) -> Path:
    p = p.expanduser().resolve()
    if p.name == "plugins" and (p.parent / MARKET_FILE).exists():
        return p.parent
    return p


def find_campaign(start: Optional[Path] = None) -> Optional[Path]:
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / CAMPAIGN_FILE).exists():
            return d
    return None


def _from_campaign() -> Optional[Path]:
    root = find_campaign()
    if not root or yaml is None:
        return None
    cfg = yaml.safe_load((root / CAMPAIGN_FILE).read_text(encoding="utf-8")) or {}
    lib = cfg.get("library")
    return _normalise(root / lib) if lib else None


def _walk_up(start: Optional[Path] = None) -> Optional[Path]:
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / MARKET_FILE).exists():
            return d
    return None


def is_forge_source(root: Path) -> bool:
    """True if `root` is the marketplace that ships the forge itself (don't build modules there)."""
    return (root / "plugins" / "solo-rpg-forge").resolve() == FORGE_ROOT


def find_library(explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        return _normalise(Path(explicit))
    env = os.environ.get("SOLO_RPG_LIBRARY")
    if env:
        return _normalise(Path(env))
    lib = _from_campaign() or _walk_up()
    if lib and is_forge_source(lib):
        return None
    return lib


def require_library(explicit: Optional[str] = None) -> Path:
    lib = find_library(explicit)
    if not lib or not (lib / MARKET_FILE).exists():
        raise SystemExit(
            "No module library found here.\n"
            "Create one in the current folder with:  module_tool.py init [--name NAME]\n"
            "or point at an existing one with SOLO_RPG_LIBRARY=<path> (or --library <path>)."
        )
    return lib


def find_core() -> Optional[Path]:
    """The solo-rpg-core plugin folder, in a source checkout or in the plugin cache.

    Source checkout: <market>/plugins/solo-rpg-core next to this plugin.
    Plugin cache:    <cache>/<market>/solo-rpg-core/<version> next to <cache>/<market>/solo-rpg-forge/<version>.
    """
    env = os.environ.get("SOLO_RPG_CORE")
    candidates = [Path(env)] if env else []
    candidates.append(FORGE_ROOT.parent / "solo-rpg-core")
    candidates += sorted((FORGE_ROOT.parents[1] / "solo-rpg-core").glob("*"), reverse=True)
    for c in candidates:
        if (c / "scripts" / "table.py").exists():
            return c.resolve()
    return None


def market_name(lib: Path) -> str:
    return json.loads((lib / MARKET_FILE).read_text(encoding="utf-8")).get("name", DEFAULT_NAME)
