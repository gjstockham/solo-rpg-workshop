#!/usr/bin/env python3
"""Scaffold, register and lint ruleset module plugins in the workshop marketplace.

  python module_tool.py scaffold MODULE_ID --title "Book Title" --kind game|solo-engine|supplement|setting
  python module_tool.py register MODULE_ID          (add/update entry in marketplace.json)
  python module_tool.py check MODULE_ID             (lint structure; runs table validation)
  python module_tool.py where                       (print workshop paths)

MODULE_ID is kebab-case and becomes the plugin name (skills appear as /MODULE_ID:skill).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

HERE = Path(__file__).resolve()
PLUGINS = HERE.parents[2]
ROOT = HERE.parents[3]
MARKET = ROOT / ".claude-plugin" / "marketplace.json"
CORE_TABLE = PLUGINS / "solo-rpg-core" / "scripts" / "table.py"

MODULE_YAML = """\
# Module manifest — read by solo-rpg-core scripts, vault-setup and session-kit.
id: {id}
title: "{title}"
kind: {kind}                 # game | solo-engine | supplement | setting
version: 0.1.0
sources:                     # the book(s) this module was built from
  - title: "{title}"
    edition: ""
    file: ""                 # original PDF filename (not the path)
    page_offset: 0           # printed page = PDF page - page_offset (if constant)
requires: []                 # other module ids this one needs (e.g. a supplement's base game)

dice:
  used: []                   # dice expressions this ruleset uses, e.g. [1d6, 2d6]
  conventions: ""            # how the book reads dice (roll-under/over, ties, doubles ...) with page

# Things the player tracks. vault-setup turns these into folders, templates and frontmatter.
records: []
#  - type: character         # singular noun, kebab-case
#    folder: Characters
#    fields:
#      - {{name: name, type: text}}
#      - {{name: stat-example, type: number, min: 0, max: 10, source: "p.12"}}

# Numeric state that changes during play (campaign, scene or record scoped).
trackers: []
#  - {{id: example-track, title: Example, scope: campaign, min: 0, max: 10, default: 5, source: "p.30"}}

# Named lists the rules tell you to maintain (and possibly roll against).
lists: []
#  - {{id: example-list, title: Example, folder: Lists/Example, pickable: true, source: "p.31"}}

# Step-by-step procedures (files in procedures/). `when` drives session-kit.
procedures: []
#  - {{id: example-procedure, title: Example, when: scene, file: procedures/example-procedure.md}}
#    when: setup | session-start | scene | encounter | downtime | session-end | on-demand
"""

PLUGIN_JSON = {
    "name": None,
    "description": None,
    "version": "0.1.0",
    "defaultEnabled": False,
    "dependencies": ["solo-rpg-core"],
    "author": {"name": "Geoff"},
}

RULES_INDEX = """\
# {title} — rules index

Every rules file below is a faithful condensation of the book with `[p.N]` markers
(printed page numbers). The rules-lawyer searches these files; keep keywords rich.

| File | Covers | Pages | Keywords |
|---|---|---|---|
"""

GLOSSARY = "# Glossary\n\nTerm — definition as the book uses it [p.N]\n"


def load_market():
    if MARKET.exists():
        return json.loads(MARKET.read_text(encoding="utf-8"))
    return {"name": "solo-rpg-workshop", "owner": {"name": "Geoff"}, "plugins": []}


def cmd_scaffold(a):
    mid = a.id
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", mid):
        sys.exit("module id must be kebab-case")
    d = PLUGINS / mid
    if (d / "module.yaml").exists() and not a.force:
        sys.exit(f"{d} already exists (use --force to re-create missing files only)")
    for sub in (".claude-plugin", "rules", "tables", "procedures", "skills/rules", "references"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    pj = dict(PLUGIN_JSON, name=mid, description=f"Rules, tables and procedures for {a.title} (solo-rpg module)")
    files = {
        d / ".claude-plugin" / "plugin.json": json.dumps(pj, indent=2) + "\n",
        d / "module.yaml": MODULE_YAML.format(id=mid, title=a.title, kind=a.kind),
        d / "rules" / "INDEX.md": RULES_INDEX.format(title=a.title),
        d / "rules" / "GLOSSARY.md": GLOSSARY,
        d / "README.md": f"# {a.title}\n\nsolo-rpg module `{mid}` ({a.kind}). Built by solo-rpg-forge.\n\n"
                          "## Build log\n\n## Known gaps\n",
    }
    for p, content in files.items():
        if not p.exists():
            p.write_text(content, encoding="utf-8")
            print(f"created {p.relative_to(ROOT)}")
    cmd_register(a)


def cmd_register(a):
    mid = a.id
    d = PLUGINS / mid
    pj = json.loads((d / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    m = load_market()
    entry = {"name": mid, "source": f"./plugins/{mid}", "description": pj.get("description", "")}
    m["plugins"] = [p for p in m["plugins"] if p.get("name") != mid] + [entry]
    MARKET.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"registered {mid} in {MARKET.relative_to(ROOT)}")


def frontmatter(p: Path):
    t = p.read_text(encoding="utf-8")
    if not t.startswith("---"):
        return None
    end = t.find("\n---", 3)
    try:
        return yaml.safe_load(t[3:end]) or {}
    except Exception as e:
        return {"_error": str(e)}


def cmd_check(a):
    d = PLUGINS / a.id
    errs, warns = [], []
    if not d.exists():
        sys.exit(f"no module at {d}")
    try:
        mod = yaml.safe_load((d / "module.yaml").read_text(encoding="utf-8")) or {}
    except Exception as e:
        sys.exit(f"module.yaml does not parse: {e}")
    for k in ("id", "title", "kind", "sources"):
        if not mod.get(k):
            errs.append(f"module.yaml: missing {k}")
    if mod.get("id") != a.id:
        errs.append(f"module.yaml id '{mod.get('id')}' != folder '{a.id}'")
    for pr in mod.get("procedures") or []:
        f = d / pr.get("file", "")
        if not pr.get("file") or not f.exists():
            errs.append(f"procedure {pr.get('id')}: file missing ({pr.get('file')})")
        elif "[p." not in f.read_text(encoding="utf-8"):
            warns.append(f"procedure {pr.get('id')}: no [p.N] citations")
    for kind in ("records", "trackers", "lists"):
        for it in mod.get(kind) or []:
            if not it.get("source") and kind != "records":
                warns.append(f"{kind} '{it.get('id')}': no source page")
    rules = sorted((d / "rules").glob("*.md"))
    if len(rules) <= 2:
        warns.append("rules/: only INDEX/GLOSSARY present")
    idx = (d / "rules" / "INDEX.md").read_text(encoding="utf-8") if (d / "rules" / "INDEX.md").exists() else ""
    for r in rules:
        if r.name in ("INDEX.md", "GLOSSARY.md"):
            continue
        if r.name not in idx:
            errs.append(f"rules/{r.name} not listed in rules/INDEX.md")
        txt = r.read_text(encoding="utf-8")
        if "[p." not in txt:
            errs.append(f"rules/{r.name}: no [p.N] page markers")
        if len(txt.splitlines()) > 400:
            warns.append(f"rules/{r.name}: {len(txt.splitlines())} lines — consider splitting")
    skills = sorted((d / "skills").glob("*/SKILL.md"))
    if not skills:
        errs.append("no skills/*/SKILL.md")
    for s in skills:
        fm = frontmatter(s)
        if fm is None or "_error" in (fm or {}):
            errs.append(f"{s.relative_to(d)}: bad or missing frontmatter")
        elif not fm.get("description"):
            errs.append(f"{s.relative_to(d)}: no description")
    m = load_market()
    if not any(p.get("name") == a.id for p in m["plugins"]):
        errs.append("not registered in marketplace.json (run register)")
    print(f"# check {a.id}")
    for e in errs:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"warn:  {w}")
    print("\n# tables")
    env = dict(**__import__("os").environ, SOLO_RPG_LIBRARY=str(PLUGINS))
    r = subprocess.run([sys.executable, str(CORE_TABLE), "validate", "--module", a.id], env=env)
    ok = not errs and r.returncode == 0
    print("\nRESULT:", "OK" if ok else "FIX ERRORS ABOVE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scaffold"); p.add_argument("id"); p.add_argument("--title", required=True)
    p.add_argument("--kind", choices=["game", "solo-engine", "supplement", "setting"], required=True)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("register"); p.add_argument("id")
    p = sub.add_parser("check"); p.add_argument("id")
    sub.add_parser("where")
    a = ap.parse_args()
    if a.cmd == "where":
        print(f"workshop:    {ROOT}\nplugins:     {PLUGINS}\nmarketplace: {MARKET}\nstaging:     {ROOT / 'staging'}")
        return 0
    return {"scaffold": cmd_scaffold, "register": cmd_register, "check": cmd_check}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
