#!/usr/bin/env python3
"""rpg-sealed: check or reveal the sealed log of secret GM rolls.

  rpg-sealed verify             integrity check; prints counts only, no results
  rpg-sealed show [--last N]    print sealed results (spoilers: for after an adventure)

`rpg-roll --secret` and `rpg-table roll --secret` write each full result to
.solo-rpg/sealed.jsonl and only its SHA-256 to .solo-rpg/audit.jsonl. `verify`
re-hashes every sealed line and matches it against the audit stubs, so an edited,
added or removed sealed line shows up without revealing any result.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def _lines(p: Path):
    if not p.exists():
        return []
    return [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def cmd_verify(root: Path) -> int:
    d = root / common.AUDIT_DIR
    sealed = Counter(common.seal_hash(ln) for ln in _lines(d / common.SEALED_FILE))
    stubs: Counter = Counter()
    for ln in _lines(d / "audit.jsonl"):
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if rec.get("secret") and rec.get("sha256"):
            stubs[rec["sha256"]] += 1
    matched = sum((sealed & stubs).values())
    unlogged = sum((sealed - stubs).values())   # sealed lines with no audit stub
    missing = sum((stubs - sealed).values())    # audit stubs whose sealed line is gone or changed
    print(f"sealed results: {sum(sealed.values())}   audit stubs: {sum(stubs.values())}   matched: {matched}")
    if unlogged or missing:
        if unlogged:
            print(f"❌ {unlogged} sealed line(s) have no matching audit stub (edited or added)")
        if missing:
            print(f"❌ {missing} audit stub(s) have no matching sealed line (edited or removed)")
        return 1
    print("✅ sealed log intact")
    return 0


def format_record(rec: dict) -> list:
    label = f" — {rec['label']}" if rec.get("label") else ""
    if rec.get("type") == "table":
        out = []
        for e in rec.get("entries", []):
            ind = "  " * e.get("depth", 0)
            body = e.get("error") or f"{e.get('value')} → {e.get('result')}"
            out.append(f"{rec['ts']}  {ind}📜 {e.get('title')} ({e.get('source')}): {body}{label}")
        return out
    return [f"{rec['ts']}  🎲 {rec.get('expression')} = {rec.get('total')}{label}"]


def cmd_show(root: Path, last: int = 0, since: str = "", until: str = "") -> int:
    """Print sealed results, optionally only those with since <= ts <= until (ISO strings)."""
    recs = [json.loads(ln) for ln in _lines(root / common.AUDIT_DIR / common.SEALED_FILE)]
    recs = [r for r in recs if (not since or r.get("ts", "") >= since) and (not until or r.get("ts", "") <= until)]
    if last:
        recs = recs[-last:]
    if not recs:
        print("No sealed results.")
    for rec in recs:
        print("\n".join(format_record(rec)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rpg-sealed", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    p = sub.add_parser("show")
    p.add_argument("--last", type=int, default=0)
    a = ap.parse_args(argv)
    root = common.find_campaign()
    if not root:
        print("ERROR: not in a campaign (no solo-rpg.yaml found)", file=sys.stderr)
        return 2
    return cmd_verify(root) if a.cmd == "verify" else cmd_show(root, a.last)


if __name__ == "__main__":
    sys.exit(main())
