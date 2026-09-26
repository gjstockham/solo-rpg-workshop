#!/usr/bin/env python3
"""rpg-gm: build and check adventure modules for GM-style solo play.

  rpg-gm where                                  print the vault's paths, rules modules, adventures
  rpg-gm scaffold [ADV_ID] --title T --requires RULES_ID [...] [--types locations npcs ...]
  rpg-gm extract PDF ADV_ID [--pages 1-40] [--columns 2] [--render all]
  rpg-gm check ADV_ID                           lint an adventure module; validates its tables
  rpg-gm init [--campaign NAME] [--rules RULES_ID ...] [--dry-run]
        set the vault up for GM play: solo-rpg.yaml, .claude/settings.json, the gm-oracle module
  rpg-gm status                                 campaign config, rules modules, adventures

Play (hidden state under <vault>/.solo-rpg/gm/<adv-id>/; --adv defaults to the active one):
  rpg-gm adventure list|start|finish|abandon [ADV_ID]
  rpg-gm set-session "Sessions/Session 03.md"
  rpg-gm state show [PATH] | state set PATH VALUE --why TEXT
  rpg-gm enter LOC_ID                           the party moves; says whether it's a first visit
  rpg-gm spawn STAT_ID [--count N|DICE] [--at LOC_ID]   hp and dice counts rolled secretly
  rpg-gm damage INSTANCE N                      e.g. stat-02#1 5 (negative heals)
  rpg-gm tick CLOCK_ID [N]
  rpg-gm canon "FACT" --basis "WHY"
  rpg-gm reveal [ADV_ID] [--force]              after an adventure: spoilers by design

An adventure module lives at <vault>/.solo-rpg/adventures/ADV_ID/ and is defined by
references/adventure-spec.md in this plugin. `extract` runs solo-rpg-forge's PDF
extractor into <vault>/.solo-rpg/staging/ADV_ID/book/.

Output names elements by id only, never by title or content, so it is safe to show
the player: tool calls are visible in Claude Code even when collapsed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gmpaths as gp  # noqa: E402
import gm_play  # noqa: E402

ROOT: Path = Path.cwd()

# The standard element vocabulary: type -> (id prefix, file extension).
# An adventure can add its own types in adventure.yaml -> types: {name: prefix}.
TYPES: Dict[str, tuple] = {
    "locations": ("loc", ".md"),
    "npcs": ("npc", ".md"),
    "stat-blocks": ("stat", ".yaml"),
    "events": ("ev", ".md"),
    "clues": ("clue", ".md"),
    "scenes": ("scn", ".md"),
    "factions": ("fac", ".md"),
    "items": ("itm", ".md"),
    "handouts": ("h", ".md"),
}
CLOCK_PREFIX = "clk"
TABLE_PREFIX = "tbl"

ADVENTURE_YAML = """\
# Adventure manifest: read by rpg-gm, the keeper and the play skills. Hidden from the player.
# Format: references/adventure-spec.md in the solo-rpg-gm plugin.
id: {id}
title: "{title}"
requires: [{requires}]       # rules module ids in this vault
sources:
  - file: ""                 # PDF filename (not the path)
    page_offset: 0           # printed page = PDF page - page_offset (if constant)
structure: ""                # site-based | event-driven | investigation | scene-based | mixed
party:                       # the adventure's own guidance, as printed
  guidance: ""
  source: ""
scaling: []                  # the adventure's own scaling notes: [{{note: "as printed", source: "p.N"}}]
start: {{element: "", note: "", source: ""}}   # where and how play begins
types: {{}}                    # element types beyond the standard vocabulary: {{name: prefix}}
elements:
{elements}
clocks: []                   # [{{id: clk-01, max: 6, source: "p.N", note: "what it counts"}}]
tables: []                   # [tbl-01, ...]; files in tables/
rules_topics: []             # rules the adventure calls on, as named in the rules module INDEX
"""

INDEX_MD = """\
# Index

Every element in this adventure. Hidden from the player.

| Id | Type | Title | Pages | One line |
|---|---|---|---|---|
"""

OVERVIEW_MD = """\
# Overview

TODO: the GM synopsis, every paragraph citing its printed page: background, what is
going on, how play begins, how it can end, anything the GM must know before play.
"""


def load_yaml(p: Path) -> Any:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def split_frontmatter(text: str):
    """Return (frontmatter dict or None, body, error)."""
    if not text.startswith("---"):
        return None, text, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, text, "frontmatter not closed"
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except Exception as e:
        return None, text[end + 4:], f"frontmatter does not parse: {e}"
    if not isinstance(fm, dict):
        return None, text[end + 4:], "frontmatter is not a mapping"
    return fm, text[end + 4:], None


def core_dice():
    core = gp.find_core()
    if core is None:
        return None
    sys.path.insert(0, str(core / "scripts"))
    try:
        import dice  # type: ignore
        return dice
    except Exception:
        return None


def is_dice(expr: Any, dice) -> bool:
    if isinstance(expr, int):
        return True
    if dice is None:
        return True  # can't check without core; don't block on it
    try:
        dice.roll(str(expr))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- where

def cmd_where(a) -> int:
    advs = sorted(p.parent.name for p in gp.adventures_dir(ROOT).glob(f"*/{gp.ADVENTURE_FILE}"))
    print(f"vault:       {ROOT}\n"
          f"adventures:  {gp.adventures_dir(ROOT)}\n"
          f"staging:     {gp.staging_dir(ROOT)}\n"
          f"pdfs:        {ROOT / 'pdfs'}\n"
          f"gm plugin:   {gp.GM_ROOT}\n"
          f"forge:       {gp.find_forge() or 'NOT FOUND (install solo-rpg-forge)'}\n"
          f"core:        {gp.find_core() or 'NOT FOUND (install solo-rpg-core)'}\n"
          f"rules:       {', '.join(gp.rules_modules(ROOT)) or 'none yet (build one with the forge)'}\n"
          f"built:       {', '.join(advs) or 'none yet'}")
    return 0


# ---------------------------------------------------------------- scaffold

def next_adventure_id() -> str:
    n = 1
    while gp.adventure_dir(ROOT, f"adv-{n:02d}").exists():
        n += 1
    return f"adv-{n:02d}"


def cmd_scaffold(a) -> int:
    aid = a.id or next_adventure_id()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", aid):
        sys.exit("adventure id must be kebab-case")
    rules = gp.rules_modules(ROOT)
    missing = [r for r in a.requires if r not in rules]
    if missing:
        sys.exit(f"rules module(s) not in this vault: {missing}. In this vault: {list(rules) or 'none'}.\n"
                 "Build the rules module with /solo-rpg-forge:ingest and /solo-rpg-forge:build-module first.")
    types = a.types or ["locations", "npcs", "stat-blocks"]
    d = gp.adventure_dir(ROOT, aid)
    if (d / gp.ADVENTURE_FILE).exists() and not a.force:
        sys.exit(f"{d} already exists (use --force to re-create missing files only)")
    for t in types:
        (d / t).mkdir(parents=True, exist_ok=True)
    (d / "tables").mkdir(parents=True, exist_ok=True)
    gp.staging_dir(ROOT, aid).mkdir(parents=True, exist_ok=True)
    elements = "\n".join(f"  {t}: []" for t in types)
    files = {
        d / gp.ADVENTURE_FILE: ADVENTURE_YAML.format(
            id=aid, title=a.title.replace('"', "'"), requires=", ".join(a.requires), elements=elements),
        d / "INDEX.md": INDEX_MD,
        d / "overview.md": OVERVIEW_MD,
        d / "README.md": f"# {aid}\n\nAdventure module built by solo-rpg-gm. Hidden from the player.\n\n"
                         "## Build log\n\n## Known gaps\n",
    }
    for p, content in files.items():
        if not p.exists():
            p.write_text(content, encoding="utf-8")
            print(f"created {p.relative_to(ROOT)}")
    print(f"adventure id: {aid}")
    return 0


# ---------------------------------------------------------------- extract

def cmd_extract(a, extra: List[str]) -> int:
    forge = gp.find_forge()
    if forge is None:
        sys.exit("solo-rpg-forge not found; install it (it provides the PDF extractor) or set SOLO_RPG_FORGE")
    pdf = Path(a.pdf)
    if not pdf.exists():
        sys.exit(f"no such PDF: {pdf}")
    out = gp.staging_dir(ROOT, a.id) / "book"
    if not any(x == "--render" or x.startswith("--render=") for x in extra):
        extra = [*extra, "--render", "all"]  # boxed text, stat blocks and maps read best from images
    cmd = [sys.executable, str(forge / "scripts" / "pdf_extract.py"), str(pdf), "--out", str(out), *extra]
    sys.stdout.flush()
    r = subprocess.run(cmd)
    if r.returncode == 0:
        print(f"\nstaging: {out}")
    return r.returncode


# ---------------------------------------------------------------- check

class Checker:
    def __init__(self, aid: str):
        self.aid = aid
        self.d = gp.adventure_dir(ROOT, aid)
        self.errs: List[str] = []
        self.warns: List[str] = []
        self.dice = core_dice()

    def err(self, m): self.errs.append(m)
    def warn(self, m): self.warns.append(m)

    def run(self) -> int:
        if not (self.d / gp.ADVENTURE_FILE).exists():
            sys.exit(f"no adventure module at {self.d}")
        try:
            man = load_yaml(self.d / gp.ADVENTURE_FILE) or {}
        except Exception as e:
            sys.exit(f"adventure.yaml does not parse: {e}")
        self.man = man
        self.check_manifest()
        self.types = dict(TYPES)
        for name, prefix in (man.get("types") or {}).items():
            if name in TYPES:
                self.err(f"adventure.yaml types: '{name}' is already a standard type")
            elif not re.fullmatch(r"[a-z]+", str(prefix)) or str(prefix) in (CLOCK_PREFIX, TABLE_PREFIX) \
                    or str(prefix) in {p for p, _ in TYPES.values()}:
                self.err(f"adventure.yaml types: '{name}' needs a new, lowercase prefix (got '{prefix}')")
            else:
                self.types[name] = (str(prefix), ".md")
        prefixes = "|".join(sorted({p for p, _ in self.types.values()} | {CLOCK_PREFIX, TABLE_PREFIX},
                                   key=len, reverse=True))
        self.ref_re = re.compile(rf"\b(?:{prefixes})-[0-9][0-9a-z]*\b")

        self.ids: Dict[str, str] = {}   # id -> type
        self.fm: Dict[str, dict] = {}
        self.body: Dict[str, str] = {}
        self.load_elements()
        self.load_clocks()
        self.table_ids = self.load_tables()
        self.check_references()
        self.check_connections()
        self.check_clocks_have_events()
        self.check_docs()
        self.check_rules_topics()
        return self.report()

    # -- manifest
    def check_manifest(self):
        m = self.man
        for k in ("id", "title", "requires", "sources", "start", "elements"):
            if not m.get(k):
                self.err(f"adventure.yaml: missing {k}")
        if m.get("id") and m["id"] != self.aid:
            self.err(f"adventure.yaml id '{m['id']}' != folder '{self.aid}'")
        for s in m.get("sources") or []:
            if not (s or {}).get("file"):
                self.warn("adventure.yaml: sources entry without a file name")
        rules = gp.rules_modules(ROOT)
        for r in m.get("requires") or []:
            if r not in rules:
                self.err(f"requires '{r}': no rules module with that id in .claude/skills/")
        party = m.get("party") or {}
        if not party.get("guidance"):
            self.warn("adventure.yaml: party guidance empty (write 'none given' if the book has none)")
        start = m.get("start") or {}
        if not isinstance(start, dict) or not start.get("element"):
            self.err("adventure.yaml: start.element missing")

    def id_ok(self, eid: str, prefix: str) -> bool:
        return bool(re.fullmatch(rf"{prefix}-[0-9][0-9a-z]*", eid))

    # -- elements
    def load_elements(self):
        listed = self.man.get("elements") or {}
        if not isinstance(listed, dict):
            self.err("adventure.yaml: elements must map type -> [ids]")
            return
        for t, ids in listed.items():
            if t not in self.types:
                self.err(f"elements: unknown type '{t}' (declare it under types: with a prefix)")
                continue
            prefix, ext = self.types[t]
            for eid in ids or []:
                eid = str(eid)
                if not self.id_ok(eid, prefix):
                    self.err(f"{t}: id '{eid}' must be '{prefix}-' plus a number (e.g. {prefix}-01, {prefix}-12b)")
                if eid in self.ids:
                    self.err(f"{eid}: listed twice")
                self.ids[eid] = t
                f = self.d / t / f"{eid}{ext}"
                if not f.exists():
                    self.err(f"{eid}: file {t}/{eid}{ext} missing")
                    continue
                if ext == ".yaml":
                    self.load_stat_block(eid, f)
                else:
                    self.load_markdown(eid, t, f)
            folder = self.d / t
            if folder.exists():
                for f in sorted(folder.glob(f"*{ext}")):
                    if f.stem not in (ids or []):
                        self.warn(f"{t}/{f.name}: file not listed in adventure.yaml elements")
        for sub in sorted(p for p in self.d.iterdir() if p.is_dir()):
            if sub.name == "tables" or not any(sub.iterdir()):
                continue
            if sub.name not in self.types:
                self.warn(f"{sub.name}/: not an element type (declare it under types: in adventure.yaml)")
            elif sub.name not in listed:
                self.warn(f"{sub.name}/: folder has files but the type isn't in adventure.yaml elements")

    def load_markdown(self, eid: str, t: str, f: Path):
        fm, body, e = split_frontmatter(f.read_text(encoding="utf-8"))
        if e or fm is None:
            self.err(f"{eid}: {e or 'no frontmatter'}")
            return
        self.fm[eid], self.body[eid] = fm, body
        self.check_common_fm(eid, fm)
        sections = re.split(r"(?m)^## ", body)[1:]
        if not sections:
            self.err(f"{eid}: no ## sections")
        for i, s in enumerate(sections, 1):
            if "[p." not in s:
                self.err(f"{eid}: section {i} has no [p.N] citation")
        bare = [ln for ln in body.splitlines() if re.match(r"\s*[-*] ", ln) and "[p." not in ln]
        if bare:
            self.warn(f"{eid}: {len(bare)} bullet(s) without [p.N]")
        if t == "locations":
            for enc in fm.get("encounters") or []:
                if not isinstance(enc, dict) or not enc.get("stat"):
                    self.err(f"{eid}: encounters entries need a stat id")
                elif not is_dice(enc.get("count", 1), self.dice):
                    self.err(f"{eid}: encounter count '{enc.get('count')}' is not a number or dice expression")

    def check_common_fm(self, eid: str, fm: dict):
        if fm.get("id") != eid:
            self.err(f"{eid}: frontmatter id is '{fm.get('id')}'")
        if not fm.get("title"):
            self.err(f"{eid}: no title")
        if not re.search(r"p\.\s*\d", str(fm.get("source", ""))):
            self.err(f"{eid}: source must give the printed page, e.g. \"p.7\"")

    def load_stat_block(self, eid: str, f: Path):
        try:
            sb = load_yaml(f) or {}
        except Exception as e:
            self.err(f"{eid}: does not parse: {e}")
            return
        self.fm[eid], self.body[eid] = sb, ""
        self.check_common_fm(eid, sb)
        if not sb.get("statline"):
            self.err(f"{eid}: no statline (the stat block verbatim)")
        fields = sb.get("fields")
        if not isinstance(fields, dict) or not fields:
            self.warn(f"{eid}: no structured fields")
            fields = {}
        hp, hp_roll = fields.get("hp", sb.get("hp")), sb.get("hp_roll")
        if hp is None and not hp_roll:
            self.warn(f"{eid}: neither fields.hp nor hp_roll (instances can't be spawned with hit points)")
        if hp is not None and not isinstance(hp, int):
            self.err(f"{eid}: hp must be a whole number (use hp_roll for dice)")
        if hp_roll and not is_dice(hp_roll, self.dice):
            self.err(f"{eid}: hp_roll '{hp_roll}' is not a dice expression")

    def load_clocks(self):
        for c in self.man.get("clocks") or []:
            cid = str((c or {}).get("id", ""))
            if not self.id_ok(cid, CLOCK_PREFIX):
                self.err(f"clocks: id '{cid}' must be '{CLOCK_PREFIX}-' plus a number")
            if not isinstance(c.get("max"), int):
                self.err(f"{cid}: max must be a whole number")
            if not re.search(r"p\.\s*\d", str(c.get("source", ""))):
                self.err(f"{cid}: no source page")
            if cid in self.ids:
                self.err(f"{cid}: listed twice")
            self.ids[cid] = "clocks"

    def load_tables(self) -> Set[str]:
        found: Dict[str, Path] = {}
        tdir = self.d / "tables"
        for p in sorted(tdir.rglob("*")) if tdir.exists() else []:
            if p.suffix.lower() not in (".yaml", ".yml") or p.name == "VERIFIED.yaml":
                continue
            try:
                data = load_yaml(p) or {}
            except Exception as e:
                self.err(f"tables/{p.relative_to(tdir)}: does not parse: {e}")
                continue
            items = data.get("tables") if isinstance(data, dict) and "tables" in data else [data]
            for t in items:
                tid = str((t or {}).get("id", ""))
                if not self.id_ok(tid, TABLE_PREFIX):
                    self.err(f"tables/{p.relative_to(tdir)}: id '{tid}' must be '{TABLE_PREFIX}-' plus a number")
                found[tid] = p
        listed = [str(t).split("/", 1)[-1] for t in self.man.get("tables") or []]
        for tid in listed:
            if tid not in found:
                self.err(f"tables: '{tid}' listed in adventure.yaml but no table file has that id")
        for tid in found:
            if tid not in listed:
                self.warn(f"tables: '{tid}' not listed in adventure.yaml")
            self.ids[tid] = "tables"
        return set(found)

    # -- cross-checks
    def check_references(self):
        start = (self.man.get("start") or {}).get("element")
        if start and start not in self.ids:
            self.err(f"start.element '{start}' is not an element")
        for eid in list(self.fm):
            fm = dict(self.fm[eid])
            fm.pop("id", None)
            text = yaml.safe_dump(fm, allow_unicode=True) + "\n" + self.body.get(eid, "")
            for ref in sorted(set(self.ref_re.findall(text))):
                if ref not in self.ids:
                    self.err(f"{eid}: refers to '{ref}', which doesn't exist")
            for enc in (fm.get("encounters") or []) if isinstance(fm.get("encounters"), list) else []:
                s = isinstance(enc, dict) and enc.get("stat")
                if s and self.ids.get(s) not in (None, "stat-blocks"):
                    self.err(f"{eid}: encounter stat '{s}' is not a stat block")
            stat = fm.get("stat")
            if stat and self.ids.get(str(stat)) not in (None, "stat-blocks"):
                self.err(f"{eid}: stat '{stat}' is not a stat block")

    def check_clocks_have_events(self):
        clocks = [e for e, t in self.ids.items() if t == "clocks"]
        used = {str(fm.get("clock")) for fm in self.fm.values() if fm.get("clock")}
        for c in clocks:
            if c not in used:
                self.warn(f"{c}: no event with clock: {c} (what happens when it fills?)")

    def check_connections(self):
        locs = [e for e, t in self.ids.items() if t == "locations" and e in self.fm]
        if not locs:
            return
        graph: Dict[str, Set[str]] = {e: set() for e in locs}
        recorded: Set[tuple] = set()
        twoway: List[tuple] = []
        for e in locs:
            for c in self.fm[e].get("connections") or []:
                if not isinstance(c, dict) or not c.get("to"):
                    self.err(f"{e}: connections entries need 'to'")
                    continue
                to = str(c["to"])
                if self.ids.get(to) != "locations":
                    self.err(f"{e}: connection to '{to}', which is not a location")
                    continue
                if c.get("visible") is False and not c.get("find"):
                    self.warn(f"{e}: hidden connection to {to} has no 'find' (how it's discovered)")
                graph[e].add(to)
                recorded.add((e, to))
                if not c.get("oneway"):
                    graph[to].add(e)
                    twoway.append((e, to))
        for e, to in twoway:
            if (to, e) not in recorded:
                self.warn(f"{e} → {to} isn't recorded in {to} (record connections in both locations)")
        start = (self.man.get("start") or {}).get("element")
        roots = {e for e in locs if self.fm[e].get("entry")}
        if start in graph:
            roots.add(start)
        if not roots:
            self.warn("no location to start from (start.element isn't a location and none has entry: true); "
                      "reachability not checked")
            return
        seen, q = set(roots), deque(roots)
        while q:
            for n in graph[q.popleft()]:
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        cut = sorted(set(locs) - seen)
        if cut:
            self.warn(f"not reachable from the start or an entry: {', '.join(cut)} "
                      "(mark entry: true if play can arrive there another way)")

    def check_docs(self):
        ov = self.d / "overview.md"
        if not ov.exists():
            self.err("overview.md missing")
        else:
            ov_text = ov.read_text(encoding="utf-8")
            if "TODO" in ov_text:
                self.err("overview.md: still the scaffold TODO")
            elif "[p." not in ov_text:
                self.err("overview.md: no [p.N] citations")
        idx = self.d / "INDEX.md"
        if not idx.exists():
            self.err("INDEX.md missing")
            return
        text = idx.read_text(encoding="utf-8")
        missing = [e for e, t in self.ids.items() if t not in ("clocks",) and not re.search(rf"\b{re.escape(e)}\b", text)]
        if missing:
            self.err(f"INDEX.md doesn't list: {', '.join(sorted(missing))}")

    def check_rules_topics(self):
        topics = self.man.get("rules_topics") or []
        if not topics:
            return
        text = ""
        rules = gp.rules_modules(ROOT)
        for r in self.man.get("requires") or []:
            p = rules.get(r, Path("-")) / "reference" / "rules" / "INDEX.md"
            if p.exists():
                text += p.read_text(encoding="utf-8").lower()
        gaps = [t for t in topics if str(t).lower() not in text]
        if gaps:
            self.warn(f"rules topics not found in the rules module INDEX: {', '.join(map(str, gaps))}")

    # -- output
    def report(self) -> int:
        counts: Dict[str, int] = {}
        for t in self.ids.values():
            counts[t] = counts.get(t, 0) + 1
        print(f"# check {self.aid}")
        print("elements: " + (", ".join(f"{t} {n}" for t, n in sorted(counts.items())) or "none"))
        for e in self.errs:
            print(f"ERROR: {e}")
        for w in self.warns:
            print(f"warn:  {w}")
        print("\n# tables")
        rc = 0
        core = gp.find_core()
        if not self.table_ids:
            print("none")
        elif core is None:
            print("ERROR: solo-rpg-core not found; run `rpg-table validate --gm --module "
                  f"{self.aid}` yourself")
            rc = 1
        else:
            env = dict(os.environ, SOLO_RPG_VAULT=str(ROOT))
            sys.stdout.flush()
            rc = subprocess.run([sys.executable, str(core / "scripts" / "table.py"), "validate", "--gm",
                                 "--module", self.aid], env=env).returncode
        ok = not self.errs and rc == 0
        print(f"\nRESULT: {'OK' if ok else 'FIX ERRORS ABOVE'} ({len(self.errs)} error(s), {len(self.warns)} warning(s))")
        return 0 if ok else 1


def cmd_check(a) -> int:
    return Checker(a.id).run()


# ---------------------------------------------------------------- init / status

CONFIG_HEADER = ("# solo-rpg campaign config (GM style) — read by rpg-roll, rpg-table, rpg-gm and the\n"
                 "# solo-rpg-gm play skills. Adventure titles here are fine: the player chose them.\n")
DEFAULT_PATHS = {
    "sessions": "Sessions",
    "templates": "Templates",
    "characters": "Characters",
    "known": "Known",
    "handouts": "Handouts",
    "campaign_note": "Campaign.md",
    "house_rules": "House Rules.md",
    "dashboards": "Dashboards",
}
ALLOW = ["Bash(rpg-roll *)", "Bash(rpg-table *)", "Bash(rpg-gm *)", "Bash(rpg-sealed verify)"]
# Tamper-evident logs: Claude appends through the scripts but never edits them.
# Obsidian's own config is the player's.
DENY = ["Edit(./.obsidian/**)", "Edit(./.solo-rpg/audit.jsonl)", "Edit(./.solo-rpg/sealed.jsonl)",
        "Edit(./.solo-rpg/gm/**/state-log.jsonl)"]


def read_config() -> dict:
    p = ROOT / gp.CAMPAIGN_FILE
    return (load_yaml(p) or {}) if p.exists() else {}


def built_adventures() -> Dict[str, Path]:
    return {p.parent.name: p.parent for p in sorted(gp.adventures_dir(ROOT).glob(f"*/{gp.ADVENTURE_FILE}"))}


def merge_settings(path: Path, dry: bool) -> None:
    s = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    perms = s.setdefault("permissions", {})
    for key, rules in (("allow", ALLOW), ("deny", DENY)):
        lst = perms.setdefault(key, [])
        lst += [r for r in rules if r not in lst]
    txt = json.dumps(s, indent=2) + "\n"
    if dry:
        print(f"--- {path}\n{txt}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(txt, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


def cmd_init(a) -> int:
    cfg = read_config()
    if cfg and cfg.get("style", "clerk") != "gm":
        sys.exit("This vault is already a clerk-style campaign (solo-rpg.yaml has no `style: gm`).\n"
                 "GM play needs its own vault: one campaign, one style.")
    campaign = a.campaign or cfg.get("campaign")
    if not campaign:
        sys.exit("give --campaign NAME")
    rules = a.rules or [m for m in cfg.get("modules") or [] if m != gp.ORACLE_ID]
    if not rules:
        sys.exit("give --rules RULES_ID (the forge-built rules module(s) this campaign uses)")
    present = gp.rules_modules(ROOT)
    missing = [r for r in rules if r not in present]
    if missing:
        sys.exit(f"rules module(s) not in this vault: {missing}. In this vault: {list(present) or 'none'}")
    for r in rules:
        m = load_yaml(present[r] / "module.yaml") or {}
        for req in m.get("requires") or []:
            if req not in rules:
                sys.exit(f"rules module {r} requires {req}; add it to --rules")

    advs = list(cfg.get("adventures") or [])
    known = {str((x or {}).get("id")) for x in advs}
    advs += [{"id": aid, "status": "planned"} for aid in built_adventures() if aid not in known]
    cfg.update({"campaign": campaign, "style": "gm", "modules": [*rules, gp.ORACLE_ID], "adventures": advs})
    for k, v in (("active_adventure", None), ("party_mode", "as-written"), ("session_log", "terse"),
                 ("current_session", None)):
        cfg.setdefault(k, v)
    paths = cfg.setdefault("paths", {})
    for k, v in DEFAULT_PATHS.items():
        paths.setdefault(k, v)
    txt = CONFIG_HEADER + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)

    oracle_src = gp.GM_ROOT / "references" / "oracle"
    oracle_dst = ROOT / gp.SKILLS / gp.ORACLE_ID
    if a.dry_run:
        print(f"--- {gp.CAMPAIGN_FILE}\n{txt}")
        print(f"--- {oracle_dst.relative_to(ROOT)}: "
              f"{'already present, kept' if oracle_dst.exists() else 'would install the gm-oracle module'}")
    else:
        (ROOT / gp.CAMPAIGN_FILE).write_text(txt, encoding="utf-8")
        print(f"wrote {gp.CAMPAIGN_FILE}")
        (ROOT / gp.WORK / "gm").mkdir(parents=True, exist_ok=True)
        print(f"ensured {gp.WORK}/ and {gp.WORK}/gm/")
        if oracle_dst.exists():
            print(f"kept {oracle_dst.relative_to(ROOT)} (already present)")
        else:
            shutil.copytree(oracle_src, oracle_dst)
            print(f"installed {oracle_dst.relative_to(ROOT)}")
    merge_settings(ROOT / ".claude" / "settings.json", a.dry_run)
    return 0


def cmd_status(a) -> int:
    cfg = read_config()
    print(f"vault: {ROOT}")
    if not cfg:
        print("no solo-rpg.yaml (run /solo-rpg-gm:gm-vault-setup)")
    else:
        print(f"campaign: {cfg.get('campaign')}   style: {cfg.get('style', 'clerk')}")
        print(f"modules: {', '.join(cfg.get('modules') or []) or 'none'}")
        print(f"active adventure: {cfg.get('active_adventure') or 'none'}")
        print(f"party mode: {cfg.get('party_mode')}   session log: {cfg.get('session_log')}")
        print(f"current session: {cfg.get('current_session') or 'none'}")
    built = built_adventures()
    listed = {str((x or {}).get("id")): (x or {}).get("status") for x in cfg.get("adventures") or []}
    print("adventures:")
    for aid in sorted(set(built) | set(listed)):
        state = listed.get(aid, "not registered (re-run rpg-gm init)")
        print(f"  {aid}: {state}{'' if aid in built else '  (NOT BUILT)'}")
    if not built and not listed:
        print("  none")
    print(f"rules modules present: {', '.join(gp.rules_modules(ROOT)) or 'none'}")
    print(f"oracle: {'installed' if (ROOT / gp.SKILLS / gp.ORACLE_ID / 'module.yaml').exists() else 'missing'}")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rpg-gm", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: discovered from the working directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("where")
    p = sub.add_parser("scaffold")
    p.add_argument("id", nargs="?", help="adventure id (default: the next free adv-NN)")
    p.add_argument("--title", required=True)
    p.add_argument("--requires", nargs="+", required=True, help="rules module id(s)")
    p.add_argument("--types", nargs="+", help=f"element types to create folders for (standard: {', '.join(TYPES)})")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("extract", help="extract an adventure PDF into staging (extra options go to pdf_extract.py)")
    p.add_argument("pdf")
    p.add_argument("id")
    p = sub.add_parser("check")
    p.add_argument("id")
    p = sub.add_parser("init", help="set the vault up for GM play")
    p.add_argument("--campaign")
    p.add_argument("--rules", nargs="+", help="rules module id(s)")
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    play = gm_play.add_parsers(sub)
    a, extra = ap.parse_known_args(argv)
    if extra and a.cmd != "extract":
        ap.error(f"unrecognized arguments: {' '.join(extra)}")

    global ROOT
    ROOT = gp.vault_root(a.vault)
    gp.check_vault(ROOT)
    if a.cmd == "extract":
        return cmd_extract(a, extra)
    if a.cmd in play:
        return gm_play.run(a.cmd, a, ROOT, play)
    return {"where": cmd_where, "scaffold": cmd_scaffold, "check": cmd_check,
            "init": cmd_init, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
