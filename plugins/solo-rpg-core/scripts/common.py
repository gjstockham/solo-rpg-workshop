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


MARKET_FILE = Path(".claude-plugin") / "marketplace.json"


def _plugins_dir(p: Path) -> Path:
    """Accept a library folder or its plugins/ folder; return the plugins/ folder."""
    p = p.expanduser().resolve()
    return p / "plugins" if (p / "plugins").is_dir() else p


def library_root() -> Path:
    """The 'plugins' folder of the player's module library (built by solo-rpg-forge).

    The library is a folder the player owns, not this plugin's install location
    (that is Claude Code's plugin cache). Discovery order:
      1. SOLO_RPG_LIBRARY (library folder or its plugins/ folder)
      2. `library:` in the campaign's solo-rpg.yaml, relative to the vault root
      3. the nearest folder at or above cwd containing .claude-plugin/marketplace.json
      4. this plugin's parent folder (source checkout of the workshop, for development)
    """
    env = os.environ.get("SOLO_RPG_LIBRARY")
    if env:
        return _plugins_dir(Path(env))
    root = find_campaign()
    if root:
        lib = (load_data(root / CAMPAIGN_FILE) or {}).get("library")
        if lib:
            return _plugins_dir(root / lib)
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / MARKET_FILE).exists() and (d / "plugins").is_dir():
            return d / "plugins"
    return Path(__file__).resolve().parents[2]


def find_campaign(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from cwd looking for solo-rpg.yaml; return the vault root."""
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
    """Map module id -> plugin dir for every plugin that has a module.yaml.

    If `only` is None and a campaign config lists modules, restrict to those.
    """
    if only is None:
        only = campaign_config().get("modules") or None
    out: Dict[str, Path] = {}
    root = library_root()
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
