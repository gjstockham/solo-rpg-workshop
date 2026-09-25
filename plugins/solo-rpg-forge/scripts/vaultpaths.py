"""Where everything lives in a campaign vault.

A module is a **project skill** in the player's own vault, not a plugin:

  <vault>/pdfs/                              rulebook PDFs the player supplies
  <vault>/.claude/skills/<module-id>/        the module (SKILL.md + module.yaml)
  <vault>/.claude/skills/<module-id>/reference/{rules,tables,procedures}/
  <vault>/.claude/agents/                    vault-specific agents
  <vault>/.solo-rpg/staging/<module-id>/     PDF extraction, SURVEY.md, BUILD-STATE.md
  <vault>/.solo-rpg/audit.jsonl              the roll/table audit trail
  <vault>/solo-rpg.yaml                      campaign config (written by vault-setup)

The forge never writes inside its own plugin folder: once installed from a
marketplace that folder is Claude Code's plugin cache, replaced on every update.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

FORGE_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_FILE = "solo-rpg.yaml"
SKILLS = Path(".claude") / "skills"
AGENTS = Path(".claude") / "agents"
WORK = ".solo-rpg"
DATA = "reference"  # module data folder inside the skill


def find_campaign(start: Optional[Path] = None) -> Optional[Path]:
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / CAMPAIGN_FILE).exists():
            return d
    return None


def _candidates(start: Path):
    """The folder and its parents, never reaching the home directory or above.

    ~/.claude is Claude Code's own user config, so a bare `.claude` marker must
    never make the home directory look like a vault.
    """
    home = Path.home().resolve()
    for d in [start, *start.parents]:
        if d != start and (d == home or d in home.parents):
            return  # reached the home directory, or something above it
        yield d


def vault_root(explicit: Optional[str] = None) -> Path:
    """The vault to build into: --vault, SOLO_RPG_VAULT, the campaign root, or cwd."""
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
        raise SystemExit(
            f"{root} is your home directory, not a campaign vault.\n"
            "cd to your Obsidian vault and restart Claude Code (or pass --vault PATH)."
        )
    if is_forge_source(root):
        raise SystemExit("This is the solo-rpg-workshop source repo, not a campaign vault.\n"
                         "Run this from your Obsidian vault instead.")


def is_forge_source(root: Path) -> bool:
    """True if `root` is the checkout that ships the forge itself."""
    return (root / "plugins" / "solo-rpg-forge").resolve() == FORGE_ROOT


def skills_dir(root: Path) -> Path:
    return root / SKILLS


def module_dir(root: Path, mid: str) -> Path:
    return root / SKILLS / mid


def data_dir(root: Path, mid: str) -> Path:
    return root / SKILLS / mid / DATA


def staging_dir(root: Path, mid: Optional[str] = None) -> Path:
    d = root / WORK / "staging"
    return d / mid if mid else d


def find_core() -> Optional[Path]:
    """The solo-rpg-core plugin folder, in a source checkout or in the plugin cache.

    Source checkout: <market>/plugins/solo-rpg-core next to this plugin.
    Plugin cache:    <cache>/<market>/solo-rpg-core/<version>.
    """
    env = os.environ.get("SOLO_RPG_CORE")
    candidates = [Path(env)] if env else []
    candidates.append(FORGE_ROOT.parent / "solo-rpg-core")
    candidates += sorted((FORGE_ROOT.parents[1] / "solo-rpg-core").glob("*"), reverse=True)
    for c in candidates:
        if (c / "scripts" / "table.py").exists():
            return c.resolve()
    return None
