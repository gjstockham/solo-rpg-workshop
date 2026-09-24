#!/usr/bin/env python3
"""rpg-roll: roll dice with an auditable result.

Examples:
  rpg-roll 2d6+1
  rpg-roll 4d6kh3 --times 6 --label "stat block"
  rpg-roll 1d100 --check "<=45" --label "skill test"
  rpg-roll 5d6>=5 --log "Sessions/Session 03.md"
  rpg-roll 1d20 1d20            (several expressions in one call)

Run `rpg-roll --help-notation` for the full dice notation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import dice  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rpg-roll", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("expr", nargs="*", help="dice expression(s), e.g. 2d6+1")
    ap.add_argument("--times", type=int, default=1, help="repeat each expression N times")
    ap.add_argument("--label", default="", help="what the roll is for (goes in the log)")
    ap.add_argument("--check", help="compare total, e.g. '>=8', '<=45'; prints PASS/FAIL and margin")
    ap.add_argument("--log", help="markdown file to append the result to")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--seed", type=int, help="TESTING ONLY: deterministic seed")
    ap.add_argument("--help-notation", action="store_true", help="print dice notation reference")
    a = ap.parse_args(argv)

    if a.help_notation:
        print(dice.__doc__)
        return 0
    if not a.expr:
        ap.error("give at least one dice expression")
    dice.set_seed(a.seed)

    results = []
    try:
        for e in a.expr:
            for _ in range(max(1, a.times)):
                results.append(dice.roll(e))
    except dice.DiceError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    out = []
    for r in results:
        rec = r.to_dict()
        rec["label"] = a.label
        line = f"🎲 `{r.expression}` → {r.breakdown()} = **{r.total}**"
        if r.kind == "successes":
            line = f"🎲 `{r.expression}` → {r.breakdown()} = **{r.total} successes**"
        if a.check:
            ok = dice.check(r.total, a.check)
            target = int("".join(ch for ch in a.check if ch.isdigit() or ch == "-"))
            margin = r.total - target
            rec.update({"check": a.check, "passed": ok, "margin": margin})
            line += f" vs {a.check}: **{'PASS' if ok else 'FAIL'}** (total−target {margin:+d})"
        if a.label:
            line += f" — _{a.label}_"
        if a.seed is not None:
            line += " [SEEDED TEST ROLL]"
            rec["seeded"] = True
        common.audit({"type": "roll", **rec})
        common.append_log(a.log, f"- {line}")
        out.append((line, rec))

    if a.json:
        print(json.dumps([rec for _, rec in out], ensure_ascii=False, indent=2))
    else:
        for line, _ in out:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
