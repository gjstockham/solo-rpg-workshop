"""Shared helpers for solo-rpg-core scripts: data loading, module library
discovery, campaign config, audit trail and session-log appends."""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

CAMPAIGN_FILE = "solo-rpg.yaml"
AUDIT_DIR = ".solo-rpg"


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is None:
        raise SystemExit("PyYAML is required for .yaml files: pip install pyyaml")
    return yaml.safe_load(text)


def load_data_str(text: str) -> Any:
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml.safe_load(text)


def dump_yaml(data: Any) -> str:
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


SKILLS_DIR = Path(".claude") / "skills"
MODULE_DATA = "reference"


def vault_root(start: Optional[Path] = None) -> Path:
    """The campaign vault: where the modules and the session notes live.

    A module is a project skill in the vault, so everything is found relative to
    the vault root rather than to this plugin (which lives in Claude Code's
    plugin cache and is replaced on every update).

      1. SOLO_RPG_VAULT
      2. the nearest folder at or above cwd holding solo-rpg.yaml
      3. the nearest folder at or above cwd holding .obsidian/ (vault not set up yet)
      4. cwd

    The search stops below the home directory: ~/.claude is Claude Code's own user
    config, so the home folder must never be mistaken for a vault.
    """
    env = os.environ.get("SOLO_RPG_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    p = (start or Path.cwd()).resolve()
    home = Path.home().resolve()
    chain: List[Path] = []
    for d in [p, *p.parents]:
        if d != p and (d == home or d in home.parents):
            break  # reached the home directory, or something above it
        chain.append(d)
    for marker in (CAMPAIGN_FILE, ".obsidian"):
        for d in chain:
            if (d / marker).exists():
                return d
    return p


def modules_root() -> Path:
    """The folder holding module skills: <vault>/.claude/skills."""
    return vault_root() / SKILLS_DIR


def module_data(mod_dir: Path) -> Path:
    """A module's data folder (rules, tables, procedures) inside its skill."""
    ref = mod_dir / MODULE_DATA
    return ref if ref.is_dir() else mod_dir


def find_campaign(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from cwd looking for solo-rpg.yaml; return the vault root, if set up."""
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / CAMPAIGN_FILE).exists():
            return d
    return None


def campaign_config() -> Dict[str, Any]:
    root = find_campaign()
    if not root:
        return {}
    cfg = load_data(root / CAMPAIGN_FILE) or {}
    cfg["_root"] = str(root)
    return cfg


def module_dirs(only: Optional[List[str]] = None) -> Dict[str, Path]:
    """Map module id -> skill dir for every skill in the vault with a module.yaml.

    If `only` is None and a campaign config lists modules, restrict to those.
    """
    if only is None:
        only = campaign_config().get("modules") or None
    out: Dict[str, Path] = {}
    root = modules_root()
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if (d / "module.yaml").exists():
            mid = d.name
            try:
                mid = (load_data(d / "module.yaml") or {}).get("id", d.name)
            except Exception:
                pass
            if only and mid not in only and d.name not in only:
                continue
            out[mid] = d
    return out


def now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def audit(record: Dict[str, Any]) -> None:
    """Append a JSON line to <vault>/.solo-rpg/audit.jsonl when in a campaign.

    This is the tamper-evident trail: every roll and table result lands here
    regardless of what gets written into the prose session log.
    """
    root = find_campaign()
    if not root:
        return
    d = root / AUDIT_DIR
    d.mkdir(exist_ok=True)
    record = {"ts": now(), **record}
    with open(d / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_log(path: Optional[str], line: str) -> None:
    """Append a markdown line to a session note (created if missing)."""
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    needs_nl = p.exists() and p.stat().st_size > 0 and not p.read_text(encoding="utf-8").endswith("\n")
    with open(p, "a", encoding="utf-8") as f:
        if needs_nl:
            f.write("\n")
        f.write(line.rstrip("\n") + "\n")
