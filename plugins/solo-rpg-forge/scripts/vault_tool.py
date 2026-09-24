#!/usr/bin/env python3
"""Deterministic helpers for campaign vaults (run from the vault root).

  python vault_tool.py modules [ID ...]          summarise module manifests (records, trackers, lists, procedures)
  python vault_tool.py init --campaign NAME --modules ID [ID ...] [--dry-run]
        writes/merges solo-rpg.yaml, .claude/settings.json (enables plugins, permissions), .solo-rpg/
  python vault_tool.py set-session "Sessions/2026-01-01 Session 01.md"
  python vault_tool.py status                    show campaign config + enabled plugins
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

HERE = Path(__file__).resolve()
PLUGINS = HERE.parents[2]
MARKET = "solo-rpg-workshop"

DEFAULT_PATHS = {
    "sessions": "Sessions",
    "templates": "Templates",
    "campaign_note": "Campaign.md",
    "house_rules": "House Rules.md",
    "dashboards": "Dashboards",
}


def manifests(ids=None):
    out = {}
    for d in sorted(PLUGINS.iterdir()):
        mf = d / "module.yaml"
        if mf.exists():
            m = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
            if ids and m.get("id") not in ids:
                continue
            out[m.get("id", d.name)] = (d, m)
    return out


def cmd_modules(a):
    ms = manifests(a.ids or None)
    if not ms:
        print(f"No modules found in {PLUGINS}")
        return 1
    for mid, (d, m) in ms.items():
        print(f"## {mid} — {m.get('title')} ({m.get('kind')})  requires: {m.get('requires') or '-'}")
        print(f"   dir: {d}")
        for k in ("records", "trackers", "lists", "procedures"):
            items = m.get(k) or []
            print(f"   {k} ({len(items)}):")
            for it in items:
                print("     - " + json.dumps(it, ensure_ascii=False))
        print()
    return 0


def merge_settings(path: Path, modules, dry):
    s = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    ep = s.setdefault("enabledPlugins", {})
    for name in ["solo-rpg-core", *modules]:
        ep[f"{name}@{MARKET}"] = True
    perms = s.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    for r in ["Bash(rpg-roll *)", "Bash(rpg-table *)"]:
        if r not in allow:
            allow.append(r)
    deny = perms.setdefault("deny", [])
    for r in ["Edit(/.obsidian/**)", "Edit(/.solo-rpg/**)"]:
        if r not in deny:
            deny.append(r)
    txt = json.dumps(s, indent=2) + "\n"
    if dry:
        print(f"--- {path}\n{txt}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(txt, encoding="utf-8")
        print(f"wrote {path}")


def cmd_init(a):
    ms = manifests(None)
    missing = [m for m in a.modules if m not in ms]
    if missing:
        sys.exit(f"Unknown module(s): {missing}. Available: {list(ms)}")
    for m in a.modules:
        for req in ms[m][1].get("requires") or []:
            if req not in a.modules:
                sys.exit(f"Module {m} requires {req}; add it to --modules")
    root = Path.cwd()
    cfg_path = root / "solo-rpg.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cfg = cfg or {}
    cfg["campaign"] = a.campaign
    cfg["modules"] = list(a.modules)
    cfg.setdefault("current_session", None)
    paths = cfg.setdefault("paths", {})
    for k, v in DEFAULT_PATHS.items():
        paths.setdefault(k, v)
    txt = ("# solo-rpg campaign config — read by rpg-roll/rpg-table and the session skills\n"
           + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    if a.dry_run:
        print(f"--- {cfg_path}\n{txt}")
    else:
        cfg_path.write_text(txt, encoding="utf-8")
        (root / ".solo-rpg").mkdir(exist_ok=True)
        print(f"wrote {cfg_path}\nensured .solo-rpg/ (audit trail)")
    merge_settings(root / ".claude" / "settings.json", a.modules, a.dry_run)
    return 0


def cmd_set_session(a):
    p = Path.cwd() / "solo-rpg.yaml"
    if not p.exists():
        sys.exit("No solo-rpg.yaml here — run init first (from the vault root)")
    text = p.read_text(encoding="utf-8")
    cfg = yaml.safe_load(text) or {}
    cfg["current_session"] = a.path
    header = "".join(l + "\n" for l in text.splitlines() if l.startswith("#"))
    p.write_text(header + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"current_session = {a.path}")
    return 0


def cmd_status(a):
    p = Path.cwd() / "solo-rpg.yaml"
    print(p.read_text(encoding="utf-8") if p.exists() else "no solo-rpg.yaml")
    s = Path.cwd() / ".claude" / "settings.json"
    if s.exists():
        print(json.dumps(json.loads(s.read_text(encoding="utf-8")).get("enabledPlugins", {}), indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("modules"); p.add_argument("ids", nargs="*")
    p = sub.add_parser("init"); p.add_argument("--campaign", required=True)
    p.add_argument("--modules", nargs="+", required=True); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("set-session"); p.add_argument("path")
    sub.add_parser("status")
    a = ap.parse_args()
    return {"modules": cmd_modules, "init": cmd_init, "set-session": cmd_set_session,
            "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
