"""Where everything lives in a GM-style campaign vault.

Adventure modules are plain data under .solo-rpg/, not skills, so Claude reaches
them deliberately and their descriptions never show up in the skill list:

  <vault>/pdfs/                              the player's PDFs
  <vault>/.claude/skills/<rules-module>/     rules module, built by solo-rpg-forge
  <vault>/.solo-rpg/adventures/<adv-id>/     adventure module (adventure.yaml)
  <vault>/.solo-rpg/staging/<adv-id>/        PDF extraction, SURVEY.md, BUILD-STATE.md
  <vault>/.solo-rpg/gm/<adv-id>/             hidden play state (from M4)

Nothing is ever written inside this plugin: once installed, its folder is Claude
Code's plugin cache and is replaced on every update.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

GM_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_FILE = "solo-rpg.yaml"
WORK = ".solo-rpg"
SKILLS = Path(".claude") / "skills"
ADVENTURE_FILE = "adventure.yaml"


def _candidates(start: Path):
    """The folder and its parents, never reaching the home directory or above
    (~/.claude is Claude Code's own config, not a vault)."""
    home = Path.home().resolve()
    for d in [start, *start.parents]:
        if d != start and (d == home or d in home.parents):
            return
        yield d


def vault_root(explicit: Optional[str] = None) -> Path:
    """The vault: --vault, SOLO_RPG_VAULT, the campaign root, an Obsidian vault, or cwd."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("SOLO_RPG_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    p = Path.cwd().resolve()
    for marker in (CAMPAIGN_FILE, ".obsidian"):
        for d in _candidates(p):
            if (d / marker).exists():
                return d
    return p


def check_vault(root: Path) -> None:
    """Refuse to treat the home directory or this repo as a campaign vault."""
    if root == Path.home().resolve():
        raise SystemExit(f"{root} is your home directory, not a campaign vault.\n"
                         "cd to your Obsidian vault and restart Claude Code (or pass --vault PATH).")
    if (root / "plugins" / "solo-rpg-gm").resolve() == GM_ROOT:
        raise SystemExit("This is the solo-rpg-workshop source repo, not a campaign vault.\n"
                         "Run this from your Obsidian vault instead.")


def adventures_dir(root: Path) -> Path:
    return root / WORK / "adventures"


def adventure_dir(root: Path, aid: str) -> Path:
    return adventures_dir(root) / aid


def staging_dir(root: Path, aid: Optional[str] = None) -> Path:
    d = root / WORK / "staging"
    return d / aid if aid else d


def rules_modules(root: Path) -> dict:
    """Map folder name -> dir for every rules module (skill with module.yaml)."""
    s = root / SKILLS
    return {p.parent.name: p.parent for p in sorted(s.glob("*/module.yaml"))} if s.exists() else {}


def _sibling(name: str, marker: str, env: str) -> Optional[Path]:
    """Another plugin from this marketplace, in a source checkout or the plugin cache.

    Source checkout: <market>/plugins/<name> next to this plugin.
    Plugin cache:    <cache>/<market>/<name>/<version>.
    """
    candidates = [Path(os.environ[env])] if os.environ.get(env) else []
    candidates.append(GM_ROOT.parent / name)
    candidates += sorted((GM_ROOT.parents[1] / name).glob("*"), reverse=True)
    for c in candidates:
        if (c / marker).exists():
            return c.resolve()
    return None


def find_core() -> Optional[Path]:
    return _sibling("solo-rpg-core", "scripts/table.py", "SOLO_RPG_CORE")


def find_forge() -> Optional[Path]:
    return _sibling("solo-rpg-forge", "scripts/pdf_extract.py", "SOLO_RPG_FORGE")
