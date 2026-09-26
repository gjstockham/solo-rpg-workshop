#!/usr/bin/env python3
"""rpg-table: deterministic random-table lookups from module data files.

The script does the roll AND the lookup, so results always come from the
table as transcribed, never from memory.

  rpg-table list [--module M] [--search TEXT]
  rpg-table show ID
  rpg-table roll ID [--mod N] [--column C] [--times N] [--label L] [--log FILE]
  rpg-table lookup ID VALUE [--column C]          (you rolled physical dice)
  rpg-table pick --items A B C [--count N]        (uniform pick from a list)
  rpg-table pick --dir FOLDER [--where k=v ...] [--count N] [--weight FIELD]
  rpg-table validate [--module M | FILE ...]
  rpg-table verify-report [--module M]            (checklist for human proof-reading)
  rpg-table mark-verified ID [ID ...]
  rpg-table schema                                (print the table file format)

GM-style campaigns:
  --gm       (any command) also load adventure modules' tables from
             .solo-rpg/adventures/; without it they are invisible. SOLO_RPG_GM=1 does the same.
  --secret   (roll, lookup) seal the result in .solo-rpg/sealed.jsonl; the audit trail
             keeps its hash and the session log says only that the GM rolled.

IDs are 'module/table-id' or just 'table-id' when unambiguous among the
active modules (those listed in the campaign's solo-rpg.yaml, else all).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import dice  # noqa: E402

SCHEMA = r"""
TABLE FILE FORMAT (YAML; one table per file, or several under a top-level `tables:` list)
Files live in <vault>/.claude/skills/<module-id>/reference/tables/ (subfolders allowed).
The file name is free; `id` is what matters.

id: encounter-example        # kebab-case, unique within the module (required)
title: Example Encounters    # as printed in the book (required)
dice: 2d6                    # expression rolled for this table (required)
                             #   anything rpg-roll accepts: 1d6, 2d6, d66, 1d100, 3d6 ...
source: {book: Core Rules, page: 42}   # page as printed in the book (required)
columns: [day, night]        # optional; then each row uses `results:` instead of `result:`
out_of_range: clamp          # clamp (default) | error — what modifiers beyond the range do
notes: >                     # optional usage text from the book (conditions, modifiers)
  Apply +1 at night.
rows:
  - range: [2, 4]            # inclusive range ...
    result: Nothing happens
  - roll: 5                  # ... or a single value ...
    result: "{{1d6}} travellers"          # {{expr}} is rolled and substituted
  - roll: [6, 8]             # ... or a list of discrete values (NOT a range)
    result: Weather turns
    then: weather-change     # also roll on another table (id or [ids]); `module/id` for another module
  - range: [9, 11]
    results: {day: A, night: B}           # when `columns` is set
  - roll: 12
    result: Roll twice more
    reroll: 2                # roll this many more times on this same table

Rules checked by `rpg-table validate`:
  * every value the dice can produce maps to exactly one row (no gaps, no overlaps)
  * `then` targets exist; column tables give every column on every row
  * d66-style dice only produce digit-concatenated values (11-16, 21-26 ... 61-66)
Human verification is tracked separately in tables/VERIFIED.yaml via `mark-verified`.
""".strip()

INLINE = re.compile(r"\{\{([^}]+)\}\}")
MAX_DEPTH = 10


# ---------------------------------------------------------------- loading

class Table:
    def __init__(self, data: Dict[str, Any], module: str, path: Path):
        self.data = data
        self.module = module
        self.path = path
        self.id = str(data.get("id", ""))

    @property
    def fqid(self) -> str:
        return f"{self.module}/{self.id}"

    @property
    def title(self) -> str:
        return self.data.get("title", self.id)

    @property
    def source(self) -> str:
        s = self.data.get("source") or {}
        if isinstance(s, dict):
            return f"{s.get('book', '?')} p.{s.get('page', '?')}"
        return str(s)

    def row_values(self, row: Dict[str, Any]) -> List[int]:
        if "range" in row:
            lo, hi = row["range"]
            return list(range(int(lo), int(hi) + 1))
        r = row.get("roll")
        if isinstance(r, list):
            return [int(x) for x in r]
        if r is None:
            return []
        return [int(r)]

    def bounds(self) -> Tuple[int, int]:
        vals = [v for row in self.data.get("rows", []) for v in self.row_values(row)]
        return (min(vals), max(vals)) if vals else (0, 0)

    def find_row(self, value: int) -> Tuple[Optional[Dict[str, Any]], int, bool]:
        """Return (row, effective_value, clamped)."""
        for row in self.data.get("rows", []):
            if value in self.row_values(row):
                return row, value, False
        if self.data.get("out_of_range", "clamp") == "clamp":
            lo, hi = self.bounds()
            eff = min(max(value, lo), hi)
            if eff != value:
                for row in self.data.get("rows", []):
                    if eff in self.row_values(row):
                        return row, eff, True
        return None, value, False


def _iter_table_files(mod_dir: Path):
    tdir = common.module_data(mod_dir) / "tables"
    if not tdir.exists():
        return
    for p in sorted(tdir.rglob("*")):
        if p.suffix.lower() in (".yaml", ".yml", ".json") and p.name != "VERIFIED.yaml":
            yield p


def load_file(p: Path, module: str) -> List[Table]:
    data = common.load_data(p) or {}
    items = data.get("tables") if isinstance(data, dict) and "tables" in data else [data]
    return [Table(t, module, p) for t in items if isinstance(t, dict)]


def load_all(only_module: Optional[str] = None) -> Dict[str, Table]:
    mods = common.module_dirs([only_module] if only_module else None)
    out: Dict[str, Table] = {}
    for mid, d in mods.items():
        for p in _iter_table_files(d):
            for t in load_file(p, mid):
                out[t.fqid] = t
    return out


def resolve(tables: Dict[str, Table], ref: str, context_module: Optional[str] = None) -> Table:
    if ref in tables:
        return tables[ref]
    if context_module and f"{context_module}/{ref}" in tables:
        return tables[f"{context_module}/{ref}"]
    hits = [t for k, t in tables.items() if k.split("/", 1)[1] == ref]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        close = [k for k in tables if ref.lower() in k.lower()]
        hint = f" Did you mean: {', '.join(close[:8])}" if close else ""
        raise SystemExit(f"ERROR: no table '{ref}'.{hint}")
    raise SystemExit(f"ERROR: '{ref}' is ambiguous: {', '.join(t.fqid for t in hits)}")


def verified_set(mod_dir: Path) -> Dict[str, str]:
    p = common.module_data(mod_dir) / "tables" / "VERIFIED.yaml"
    if not p.exists():
        return {}
    return common.load_data(p) or {}


# ---------------------------------------------------------------- rolling

def _substitute_inline(text: str, trail: List[str]) -> str:
    def rep(m):
        r = dice.roll(m.group(1))
        trail.append(f"`{m.group(1)}` → {r.breakdown()} = {r.total}")
        return str(r.total)
    return INLINE.sub(rep, text)


def _row_text(t: Table, row: Dict[str, Any], column: Optional[str], trail: List[str]) -> str:
    if "results" in row:
        res = row["results"]
        if column:
            if column not in res:
                raise SystemExit(f"ERROR: column '{column}' not in {list(res)}")
            return _substitute_inline(str(res[column]), trail)
        return "; ".join(f"{k}: {_substitute_inline(str(v), trail)}" for k, v in res.items())
    return _substitute_inline(str(row.get("result", "")), trail)


def do_roll(tables, t: Table, mod: int, column: Optional[str], depth: int = 0,
            forced: Optional[int] = None) -> List[Dict[str, Any]]:
    if depth > MAX_DEPTH:
        return [{"table": t.fqid, "error": "max chain depth reached"}]
    if forced is None:
        r = dice.roll(t.data["dice"])
        raw, breakdown = r.total, r.breakdown()
    else:
        raw, breakdown = forced, "given"
    value = raw + mod
    row, eff, clamped = t.find_row(value)
    trail: List[str] = []
    entry: Dict[str, Any] = {
        "table": t.fqid, "title": t.title, "source": t.source, "dice": t.data["dice"],
        "roll": raw, "breakdown": breakdown, "modifier": mod, "value": value,
        "depth": depth,
    }
    if row is None:
        entry["error"] = f"no row for {value} (table covers {t.bounds()})"
        return [entry]
    entry["effective"] = eff
    entry["clamped"] = clamped
    entry["result"] = _row_text(t, row, column, trail)
    if trail:
        entry["inline_rolls"] = trail
    out = [entry]
    for _ in range(int(row.get("reroll", 0) or 0)):
        out += do_roll(tables, t, 0, column, depth + 1)
    thens = row.get("then")
    if thens:
        for ref in thens if isinstance(thens, list) else [thens]:
            out += do_roll(tables, resolve(tables, ref, t.module), 0, None, depth + 1)
    return out


def fmt_entry(e: Dict[str, Any]) -> str:
    ind = "  " * e.get("depth", 0)
    if "error" in e:
        return f"{ind}⚠️ {e['table']}: {e['error']}"
    mod = f"{e['modifier']:+d}" if e["modifier"] else ""
    clamp = f" (clamped to {e['effective']})" if e.get("clamped") else ""
    s = (f"{ind}📜 **{e['title']}** ({e['source']}): `{e['dice']}{mod}` → "
         f"{e['breakdown']}{mod} = {e['value']}{clamp} → **{e['result']}**")
    for tr in e.get("inline_rolls", []):
        s += f"\n{ind}   ↳ {tr}"
    return s


# ---------------------------------------------------------------- pick

def read_frontmatter(p: Path) -> Dict[str, Any]:
    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return common.load_data_str(text[3:end]) or {}
    except Exception:
        return {}


def cmd_pick(a) -> int:
    items: List[Tuple[str, float]] = []
    if a.items:
        items = [(x, 1.0) for x in a.items]
    elif a.dir:
        base = Path(a.dir)
        for p in sorted(base.rglob("*.md")):
            fm = read_frontmatter(p)
            ok = True
            for cond in a.where or []:
                k, _, v = cond.partition("=")
                if str(fm.get(k, "")).lower() != v.lower():
                    ok = False
            if ok:
                w = float(fm.get(a.weight, 1) or 0) if a.weight else 1.0
                if w > 0:
                    items.append((p.stem, w))
    if not items:
        print("ERROR: nothing to pick from", file=sys.stderr)
        return 2
    chosen = []
    pool = list(items)
    for _ in range(min(a.count, len(pool)) if not a.replace else a.count):
        total = sum(w for _, w in pool)
        x = dice._rng.random() * total
        acc = 0.0
        for i, (name, w) in enumerate(pool):
            acc += w
            if x < acc:
                chosen.append(name)
                if not a.replace:
                    pool.pop(i)
                break
    line = f"🎯 pick from {len(items)} → **{', '.join(chosen)}**" + (f" — _{a.label}_" if a.label else "")
    common.audit({"type": "pick", "from": [n for n, _ in items], "chosen": chosen, "label": a.label})
    common.append_log(a.log, f"- {line}")
    print(json.dumps({"chosen": chosen, "from": len(items)}) if a.json else line)
    return 0


# ---------------------------------------------------------------- validate

def validate_table(t: Table, all_tables: Dict[str, Table]) -> Tuple[List[str], List[str]]:
    errs, warns = [], []
    d = t.data
    for key in ("id", "title", "dice", "rows"):
        if key not in d:
            errs.append(f"missing '{key}'")
    if errs:
        return errs, warns
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", t.id):
        warns.append("id should be kebab-case")
    if "source" not in d:
        errs.append("missing 'source' (book + page) — needed for proof-reading and citations")
    try:
        possible = dice.possible_values(d["dice"])
    except dice.DiceError as e:
        return [f"bad dice '{d['dice']}': {e}"], warns
    cols = d.get("columns")
    seen: Dict[int, int] = {}
    for i, row in enumerate(d["rows"]):
        where = f"row {i + 1}"
        if not any(k in row for k in ("range", "roll")):
            errs.append(f"{where}: needs 'range' or 'roll'")
            continue
        if "range" in row:
            r = row["range"]
            if not (isinstance(r, list) and len(r) == 2 and int(r[0]) <= int(r[1])):
                errs.append(f"{where}: range must be [low, high]")
                continue
        if cols:
            res = row.get("results")
            if not isinstance(res, dict):
                errs.append(f"{where}: column table rows need 'results' mapping")
            else:
                missing = [c for c in cols if c not in res]
                if missing:
                    errs.append(f"{where}: missing columns {missing}")
        elif "result" not in row:
            errs.append(f"{where}: needs 'result'")
        for v in t.row_values(row):
            if v in seen:
                errs.append(f"value {v} in both row {seen[v]} and row {i + 1}")
            seen[v] = i + 1
        for ref in (row.get("then") if isinstance(row.get("then"), list) else [row.get("then")]):
            if ref:
                try:
                    resolve(all_tables, ref, t.module)
                except SystemExit as e:
                    errs.append(f"{where}: then → {e}")
        for m in INLINE.finditer(str(row.get("result", "")) + str(row.get("results", ""))):
            try:
                dice.roll(m.group(1))
            except dice.DiceError as e:
                errs.append(f"{where}: bad inline dice {{{{{m.group(1)}}}}}: {e}")
    if possible is not None:
        gaps = [v for v in possible if v not in seen]
        extra = sorted(v for v in seen if v not in possible)
        if re.fullmatch(r"\d*d([2-9])\1{1,2}", str(d["dice"]).strip().lower()):
            extra = []  # d66-style ranges naturally span impossible values like 17-20
        if gaps:
            errs.append(f"no row for possible roll(s): {_compress(gaps)}")
        if extra:
            warns.append(f"rows for values the dice can't roll unmodified: {_compress(extra)} "
                         f"(fine if the book applies modifiers)")
    else:
        warns.append("dice too complex for coverage check; checked overlaps only")
    return errs, warns


def _compress(vals: List[int]) -> str:
    if not vals:
        return ""
    out, start, prev = [], vals[0], vals[0]
    for v in vals[1:] + [None]:
        if v is not None and v == prev + 1:
            prev = v
            continue
        out.append(str(start) if start == prev else f"{start}-{prev}")
        if v is not None:
            start = prev = v
    return ", ".join(out)


def cmd_validate(a) -> int:
    if a.files:
        tables: Dict[str, Table] = {}
        for f in a.files:
            p = Path(f)
            mod = p.resolve().parent
            while mod.parent != mod and not (mod / "module.yaml").exists():
                mod = mod.parent
            mid = mod.name if (mod / "module.yaml").exists() else "local"
            for t in load_file(p, mid):
                tables[t.fqid] = t
        everything = {**load_all(), **tables}
    else:
        tables = load_all(a.module)
        everything = load_all()
    n_err = 0
    ids: Dict[str, str] = {}
    for fq, t in sorted(tables.items()):
        errs, warns = validate_table(t, everything)
        if fq in ids:
            errs.append(f"duplicate id also in {ids[fq]}")
        ids[fq] = str(t.path)
        status = "❌" if errs else ("⚠️" if warns else "✅")
        if errs or warns or a.verbose:
            print(f"{status} {fq}  [{t.path.name}]")
            for e in errs:
                print(f"    ERROR: {e}")
            for w in warns:
                print(f"    warn:  {w}")
        n_err += len(errs)
    print(f"\n{len(tables)} table(s) checked, {n_err} error(s).")
    return 1 if n_err else 0


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rpg-table", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    gm = argparse.ArgumentParser(add_help=False)
    gm.add_argument("--gm", action="store_true", help="include adventure modules' tables (GM campaigns)")

    p = sub.add_parser("list", parents=[gm]); p.add_argument("--module"); p.add_argument("--search")
    p = sub.add_parser("show", parents=[gm]); p.add_argument("id")
    for name in ("roll", "lookup"):
        p = sub.add_parser(name, parents=[gm])
        p.add_argument("id")
        if name == "lookup":
            p.add_argument("value", type=int)
        p.add_argument("--mod", type=int, default=0)
        p.add_argument("--column")
        p.add_argument("--times", type=int, default=1)
        p.add_argument("--label", default="")
        p.add_argument("--log")
        p.add_argument("--json", action="store_true")
        p.add_argument("--seed", type=int, help="TESTING ONLY")
        p.add_argument("--secret", action="store_true",
                       help="GM roll the characters don't know about: seal the result, log only that a roll was made")
    p = sub.add_parser("pick")
    p.add_argument("--items", nargs="+"); p.add_argument("--dir")
    p.add_argument("--where", nargs="*"); p.add_argument("--weight")
    p.add_argument("--count", type=int, default=1); p.add_argument("--replace", action="store_true")
    p.add_argument("--label", default=""); p.add_argument("--log"); p.add_argument("--json", action="store_true")
    p.add_argument("--seed", type=int, help="TESTING ONLY")
    p = sub.add_parser("validate", parents=[gm]); p.add_argument("files", nargs="*"); p.add_argument("--module")
    p.add_argument("-v", "--verbose", action="store_true")
    p = sub.add_parser("verify-report", parents=[gm]); p.add_argument("--module")
    p = sub.add_parser("mark-verified", parents=[gm]); p.add_argument("ids", nargs="+")
    sub.add_parser("schema")
    a = ap.parse_args(argv)
    if getattr(a, "gm", False):
        common.GM_MODE = True

    if a.cmd == "schema":
        print(SCHEMA)
        return 0
    if a.cmd == "validate":
        return cmd_validate(a)
    if a.cmd == "pick":
        dice.set_seed(a.seed)
        return cmd_pick(a)

    tables = load_all(getattr(a, "module", None) if a.cmd in ("list", "verify-report") else None)

    if a.cmd == "list":
        mods = common.module_dirs()
        for fq, t in sorted(tables.items()):
            if a.search and a.search.lower() not in (fq + " " + t.title).lower():
                continue
            ver = "✓" if t.id in verified_set(mods.get(t.module, Path("."))) else " "
            print(f"{ver} {fq:45} {t.data.get('dice', '?'):8} {t.title}  ({t.source})")
        if not tables:
            print("No tables found. Modules are looked for in:", common.modules_root())
        return 0

    if a.cmd == "verify-report":
        mods = common.module_dirs([a.module] if a.module else None)
        by_page: Dict[str, List[Table]] = {}
        for t in tables.values():
            by_page.setdefault(t.source, []).append(t)
        print("# Table proof-reading checklist\n")
        print("Compare each table against the printed page; tick when every row matches.\n")
        for src in sorted(by_page, key=lambda s: (s.split(" p.")[0], int(re.sub(r"\D", "", s.split("p.")[-1]) or 0))):
            for t in by_page[src]:
                v = "x" if t.id in verified_set(mods.get(t.module, Path("."))) else " "
                print(f"- [{v}] **{t.title}** — {src} — `{t.fqid}` ({len(t.data.get('rows', []))} rows, `{t.data.get('dice')}`)")
        return 0

    if a.cmd == "mark-verified":
        mods = common.module_dirs(None)
        for ref in a.ids:
            t = resolve(tables, ref)
            p = common.module_data(mods[t.module]) / "tables" / "VERIFIED.yaml"
            data = verified_set(mods[t.module])
            data[t.id] = common.now()
            p.write_text(common.dump_yaml(data), encoding="utf-8")
            print(f"✓ {t.fqid}")
        return 0

    t = resolve(tables, a.id)

    if a.cmd == "show":
        print(f"# {t.title}  ({t.fqid})\nSource: {t.source}   Dice: {t.data['dice']}\n")
        if t.data.get("notes"):
            print(t.data["notes"].strip() + "\n")
        for row in t.data["rows"]:
            vals = t.row_values(row)
            key = f"{vals[0]}-{vals[-1]}" if "range" in row and len(vals) > 1 else ",".join(map(str, vals))
            txt = row.get("result") if "result" in row else row.get("results")
            extra = ""
            if row.get("then"):
                extra += f"  → then {row['then']}"
            if row.get("reroll"):
                extra += f"  → reroll x{row['reroll']}"
            print(f"{key:>8}  {txt}{extra}")
        return 0

    dice.set_seed(a.seed)
    all_entries = []
    for _ in range(max(1, a.times)):
        forced = a.value if a.cmd == "lookup" else None
        entries = do_roll(tables, t, a.mod, a.column, forced=forced)
        all_entries.append(entries)
        text = "\n".join(fmt_entry(e) for e in entries)
        if a.label:
            text += f" — _{a.label}_"
        if a.seed is not None:
            text += " [SEEDED TEST ROLL]"
        if a.secret:
            # One sealed record per roll, chained results included, so the
            # table's title never reaches the audit trail or the session log.
            common.seal({"type": "table", "label": a.label, "seeded": a.seed is not None,
                         "entries": entries}, a.label)
            text += " [SECRET]"
            common.append_log(a.log, "- 🔒 GM rolled on a table (hidden)" + (f" — _{a.label}_" if a.label else ""))
        else:
            for e in entries:
                common.audit({"type": "table", "label": a.label, "seeded": a.seed is not None, **e})
            common.append_log(a.log, "\n".join(f"- {ln}" if i == 0 else f"  {ln}" for i, ln in enumerate(text.splitlines())))
        if not a.json:
            print(text)
    if a.json:
        print(json.dumps(all_entries, ensure_ascii=False, indent=2))
    return 1 if any("error" in e for es in all_entries for e in es) else 0


if __name__ == "__main__":
    sys.exit(main())
