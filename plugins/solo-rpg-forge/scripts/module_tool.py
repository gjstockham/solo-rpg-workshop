#!/usr/bin/env python3
"""Scaffold and lint ruleset modules inside a campaign vault.

  python module_tool.py scaffold MODULE_ID --title "Book Title" --kind game|solo-engine|supplement|setting
  python module_tool.py check MODULE_ID             (lint structure; runs table validation)
  python module_tool.py where                       (print the vault's paths)

A module is a project skill at <vault>/.claude/skills/MODULE_ID/, with its rules,
tables and procedures under reference/. The vault is found from the working
directory (see vaultpaths.py); --vault PATH overrides. Nothing is ever written
inside the forge plugin.

MODULE_ID is kebab-case and becomes the skill name, so the player types /MODULE_ID.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultpaths as vp  # noqa: E402

ROOT: Path = Path.cwd()

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

# Step-by-step procedures (files in reference/procedures/). `when` drives session-kit.
procedures: []
#  - {{id: example-procedure, title: Example, when: scene, file: reference/procedures/example-procedure.md}}
#    when: setup | session-start | scene | encounter | downtime | session-end | on-demand
"""

SKILL_MD = """\
---
name: {id}
description: "{title} rules reference. TODO: 6-12 key topics and 3-6 distinctive terms, so this
  triggers whenever play or a procedure touches {title} mechanics, terms or tables."
user-invocable: false
---
# {title}

Module data: `${{CLAUDE_SKILL_DIR}}/reference/`

- Rules: `reference/rules/` — start at `reference/rules/INDEX.md` (file → topics → pages → keywords),
  then `reference/rules/GLOSSARY.md`.
- Tables: `rpg-table list --module {id}`. Never recite a table from memory; roll or look it up.
- Procedures: `reference/procedures/`.

TODO (build-module fills these in): the core loop in one paragraph, cited. Dice conventions,
cited. The procedure list: id — when — one line each.

For any non-trivial rules question, use /solo-rpg-core:rules, which cites or abstains.
"""

RULES_INDEX = """\
# {title} — rules index

Every rules file below is a faithful condensation of the book with `[p.N]` markers
(printed page numbers). The rules-lawyer searches these files; keep keywords rich.

| File | Covers | Pages | Keywords |
|---|---|---|---|
"""

GLOSSARY = "# Glossary\n\nTerm — definition as the book uses it [p.N]\n"


def cmd_scaffold(a):
    mid = a.id
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", mid):
        sys.exit("module id must be kebab-case")
    d = vp.module_dir(ROOT, mid)
    if (d / "module.yaml").exists() and not a.force:
        sys.exit(f"{d} already exists (use --force to re-create missing files only)")
    ref = d / vp.DATA
    for sub in (ref / "rules", ref / "tables", ref / "procedures"):
        sub.mkdir(parents=True, exist_ok=True)
    files = {
        d / "SKILL.md": SKILL_MD.format(id=mid, title=a.title),
        d / "module.yaml": MODULE_YAML.format(id=mid, title=a.title, kind=a.kind),
        ref / "rules" / "INDEX.md": RULES_INDEX.format(title=a.title),
        ref / "rules" / "GLOSSARY.md": GLOSSARY,
        ref / "README.md": f"# {a.title}\n\nsolo-rpg module `{mid}` ({a.kind}). Built by solo-rpg-forge.\n\n"
                           "## Build log\n\n## Known gaps\n",
    }
    for p, content in files.items():
        if not p.exists():
            p.write_text(content, encoding="utf-8")
            print(f"created {p.relative_to(ROOT)}")
    return 0


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
    d = vp.module_dir(ROOT, a.id)
    ref = d / vp.DATA
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
        errs.append(f"module.yaml id '{mod.get('id')}' != skill folder '{a.id}'")
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
    rules = sorted((ref / "rules").glob("*.md"))
    if len(rules) <= 2:
        warns.append("reference/rules/: only INDEX/GLOSSARY present")
    idx_path = ref / "rules" / "INDEX.md"
    idx = idx_path.read_text(encoding="utf-8") if idx_path.exists() else ""
    for r in rules:
        if r.name in ("INDEX.md", "GLOSSARY.md"):
            continue
        if r.name not in idx:
            errs.append(f"reference/rules/{r.name} not listed in reference/rules/INDEX.md")
        txt = r.read_text(encoding="utf-8")
        if "[p." not in txt:
            errs.append(f"reference/rules/{r.name}: no [p.N] page markers")
        if len(txt.splitlines()) > 400:
            warns.append(f"reference/rules/{r.name}: {len(txt.splitlines())} lines — consider splitting")
    # The module's own skill, plus one runner skill per player-facing procedure.
    fm = frontmatter(d / "SKILL.md") if (d / "SKILL.md").exists() else None
    if fm is None or "_error" in (fm or {}):
        errs.append("SKILL.md: missing, or bad frontmatter")
    else:
        if not fm.get("description"):
            errs.append("SKILL.md: no description")
        elif "TODO" in fm["description"]:
            errs.append("SKILL.md: description is still the scaffold TODO")
    runners = sorted(p for p in vp.skills_dir(ROOT).glob(f"{a.id}-*/SKILL.md"))
    for s in runners:
        f = frontmatter(s)
        if f is None or "_error" in (f or {}):
            errs.append(f"{s.parent.name}/SKILL.md: bad or missing frontmatter")
        elif not f.get("description"):
            errs.append(f"{s.parent.name}/SKILL.md: no description")
    print(f"# check {a.id}")
    print(f"module:  {d}")
    print(f"runners: {len(runners)} ({', '.join(s.parent.name for s in runners) or 'none'})")
    for e in errs:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"warn:  {w}")
    print("\n# tables")
    core = vp.find_core()
    if core is None:
        print(f"ERROR: solo-rpg-core not found (set SOLO_RPG_CORE); run `rpg-table validate --module {a.id}` yourself")
        return 1
    env = dict(os.environ, SOLO_RPG_VAULT=str(ROOT))
    sys.stdout.flush()
    r = subprocess.run([sys.executable, str(core / "scripts" / "table.py"), "validate", "--module", a.id], env=env)
    ok = not errs and r.returncode == 0
    print("\nRESULT:", "OK" if ok else "FIX ERRORS ABOVE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: discovered from the working directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scaffold"); p.add_argument("id"); p.add_argument("--title", required=True)
    p.add_argument("--kind", choices=["game", "solo-engine", "supplement", "setting"], required=True)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("check"); p.add_argument("id")
    sub.add_parser("where")
    a = ap.parse_args()

    global ROOT
    ROOT = vp.vault_root(a.vault)
    vp.check_vault(ROOT)
    if a.cmd == "where":
        mods = sorted(p.parent.name for p in vp.skills_dir(ROOT).glob("*/module.yaml"))
        print(f"vault:    {ROOT}\nskills:   {vp.skills_dir(ROOT)}\nagents:   {ROOT / vp.AGENTS}\n"
              f"staging:  {vp.staging_dir(ROOT)}\npdfs:     {ROOT / 'pdfs'}\n"
              f"forge:    {vp.FORGE_ROOT}\ncore:     {vp.find_core() or 'NOT FOUND'}\n"
              f"modules:  {', '.join(mods) or 'none yet'}")
        return 0
    return {"scaffold": cmd_scaffold, "check": cmd_check}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
