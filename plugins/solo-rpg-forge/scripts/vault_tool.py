#!/usr/bin/env python3
"""Deterministic helpers for campaign vaults (run from the vault root).

  python vault_tool.py modules [ID ...]          summarise the vault's module manifests
  python vault_tool.py init --campaign NAME --modules ID [ID ...] [--dry-run]
        writes/merges solo-rpg.yaml, .claude/settings.json (permissions), .solo-rpg/
  python vault_tool.py set-session "Sessions/2026-01-01 Session 01.md"
  python vault_tool.py status                    show campaign config + modules
  python vault_tool.py guardrails                print the path of solo-rpg-core's play contract

Modules are project skills in this vault (<vault>/.claude/skills/<id>/), so there is
nothing to install or enable: they load because the vault is the project.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultpaths as vp  # noqa: E402

ROOT: Path = Path.cwd()

DEFAULT_PATHS = {
    "sessions": "Sessions",
    "templates": "Templates",
    "campaign_note": "Campaign.md",
    "house_rules": "House Rules.md",
    "dashboards": "Dashboards",
}


def manifests(ids=None):
    out = {}
    skills = vp.skills_dir(ROOT)
    if not skills.exists():
        return out
    for mf in sorted(skills.glob("*/module.yaml")):
        m = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
        mid = m.get("id", mf.parent.name)
        if ids and mid not in ids:
            continue
        out[mid] = (mf.parent, m)
    return out


def cmd_modules(a):
    ms = manifests(a.ids or None)
    if not ms:
        print(f"No modules in {vp.skills_dir(ROOT)}\nBuild one with /solo-rpg-forge:ingest <book.pdf>")
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


def merge_settings(path: Path, dry):
    s = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    perms = s.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    for r in ["Bash(rpg-roll *)", "Bash(rpg-table *)"]:
        if r not in allow:
            allow.append(r)
    deny = perms.setdefault("deny", [])
    # The audit trail and the sealed log of secret rolls are tamper-evident, so
    # Claude may append to them through the scripts but never edit them.
    # Obsidian's own config is the player's.
    for r in ["Edit(./.obsidian/**)", "Edit(./.solo-rpg/audit.jsonl)", "Edit(./.solo-rpg/sealed.jsonl)"]:
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
        sys.exit(f"Unknown module(s): {missing}. In this vault: {list(ms) or 'none'}")
    for m in a.modules:
        for req in ms[m][1].get("requires") or []:
            if req not in a.modules:
                sys.exit(f"Module {m} requires {req}; add it to --modules")
    cfg_path = ROOT / "solo-rpg.yaml"
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
        (ROOT / vp.WORK).mkdir(exist_ok=True)
        print(f"wrote {cfg_path}\nensured {vp.WORK}/ (audit trail)")
    merge_settings(ROOT / ".claude" / "settings.json", a.dry_run)
    return 0


def cmd_set_session(a):
    p = ROOT / "solo-rpg.yaml"
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
    p = ROOT / "solo-rpg.yaml"
    print(f"vault: {ROOT}\n")
    print(p.read_text(encoding="utf-8") if p.exists() else "no solo-rpg.yaml (run vault-setup)")
    print(f"modules present: {', '.join(manifests(None)) or 'none'}")
    return 0


def cmd_guardrails(a):
    core = vp.find_core()
    if core is None:
        sys.exit("solo-rpg-core not found. Is it installed? (or set SOLO_RPG_CORE)")
    print(core / "references" / "guardrails.md")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: discovered from the working directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("modules"); p.add_argument("ids", nargs="*")
    p = sub.add_parser("init"); p.add_argument("--campaign", required=True)
    p.add_argument("--modules", nargs="+", required=True); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("set-session"); p.add_argument("path")
    sub.add_parser("status")
    sub.add_parser("guardrails")
    a = ap.parse_args()

    global ROOT
    ROOT = vp.vault_root(a.vault)
    if a.cmd != "guardrails":
        vp.check_vault(ROOT)
    return {"modules": cmd_modules, "init": cmd_init, "set-session": cmd_set_session,
            "status": cmd_status, "guardrails": cmd_guardrails}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
