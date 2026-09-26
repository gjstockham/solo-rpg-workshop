"""Play-time commands for rpg-gm: adventures, hidden state, instances, clocks, canon, reveal.

Hidden state for an adventure lives at <vault>/.solo-rpg/gm/<adv-id>/:
  state.yaml         the world as it stands (changed only through these commands)
  state-log.jsonl    every change: old -> new, with why (Claude may not edit it)
  canon.md           every improvised fact, so it stays true

Output names things by id (loc-05, stat-02#1, clk-01), except `reveal`, which is for
after the adventure and shows everything.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

import gmpaths as gp

ROOT: Path = Path.cwd()
PAUSED, ACTIVE = "paused", "active"
CANON_HEADER = "# Canon: {aid}\n\nImprovised facts, in play order. Hidden from the player.\n\n"


def now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def load_yaml(p: Path) -> Any:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def core():
    """solo-rpg-core's common and dice modules (for sealed rolls)."""
    c = gp.find_core()
    if c is None:
        sys.exit("solo-rpg-core not found; install it (or set SOLO_RPG_CORE)")
    sys.path.insert(0, str(c / "scripts"))
    import common  # type: ignore
    import dice  # type: ignore
    return common, dice


# ---------------------------------------------------------------- config

def load_cfg() -> dict:
    p = ROOT / gp.CAMPAIGN_FILE
    if not p.exists():
        sys.exit("no solo-rpg.yaml here: set the vault up with /solo-rpg-gm:gm-vault-setup first")
    cfg = load_yaml(p) or {}
    if cfg.get("style") != "gm":
        sys.exit("this vault isn't a GM-style campaign (solo-rpg.yaml has no `style: gm`)")
    return cfg


def save_cfg(cfg: dict) -> None:
    p = ROOT / gp.CAMPAIGN_FILE
    header = "".join(ln + "\n" for ln in p.read_text(encoding="utf-8").splitlines() if ln.startswith("#"))
    p.write_text(header + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")


def adventure_entry(cfg: dict, aid: str) -> dict:
    for e in cfg.setdefault("adventures", []):
        if str(e.get("id")) == aid:
            return e
    e = {"id": aid, "status": "planned"}
    cfg["adventures"].append(e)
    return e


def resolve_adv(cfg: dict, explicit: Optional[str]) -> str:
    aid = explicit or cfg.get("active_adventure")
    if not aid:
        sys.exit("no active adventure: start one with `rpg-gm adventure start <id>`")
    if not (gp.adventure_dir(ROOT, aid) / gp.ADVENTURE_FILE).exists():
        sys.exit(f"adventure '{aid}' isn't built in this vault")
    return aid


def manifest(aid: str) -> dict:
    return load_yaml(gp.adventure_dir(ROOT, aid) / gp.ADVENTURE_FILE) or {}


# ---------------------------------------------------------------- state

def gm_dir(aid: str) -> Path:
    return ROOT / gp.WORK / "gm" / aid


def load_state(aid: str) -> dict:
    p = gm_dir(aid) / "state.yaml"
    if not p.exists():
        sys.exit(f"no state for {aid}: start it with `rpg-gm adventure start {aid}`")
    return load_yaml(p) or {}


def save_state(aid: str, st: dict) -> None:
    (gm_dir(aid) / "state.yaml").write_text(
        "# Hidden world state. Change it with rpg-gm, so every change is logged.\n"
        + yaml.safe_dump(st, sort_keys=False, allow_unicode=True), encoding="utf-8")


def log_change(aid: str, op: str, path: str, old: Any, new: Any, why: str = "") -> None:
    rec = {"ts": now(), "op": op, "path": path, "old": old, "new": new, "why": why}
    with open(gm_dir(aid) / "state-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def get_path(d: dict, dotted: str) -> Any:
    cur: Any = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def set_path(d: dict, dotted: str, value: Any) -> Any:
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        if not isinstance(cur.get(k), dict):
            cur[k] = {}
        cur = cur[k]
    old = cur.get(keys[-1])
    if value is None:
        cur.pop(keys[-1], None)
    else:
        cur[keys[-1]] = value
    return old


def short(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


# ---------------------------------------------------------------- adventure

def new_state(aid: str) -> dict:
    m = manifest(aid)
    start = (m.get("start") or {}).get("element")
    return {
        "adventure": aid,
        "current": start,
        "time": {"elapsed": 0, "unit": ""},
        "elements": {},
        "instances": {},
        "flags": {},
        "clocks": {str(c.get("id")): 0 for c in m.get("clocks") or []},
        "taken": [],
    }


def cmd_adventure(a) -> int:
    cfg = load_cfg()
    built = sorted(p.parent.name for p in gp.adventures_dir(ROOT).glob(f"*/{gp.ADVENTURE_FILE}"))
    if a.action == "list":
        entries = {str(e.get("id")): e for e in cfg.get("adventures") or []}
        for aid in sorted(set(built) | set(entries)):
            e = entries.get(aid, {})
            title = manifest(aid).get("title", "?") if aid in built else "(not built)"
            mark = "▶ " if aid == cfg.get("active_adventure") else "  "
            dates = "".join(f"  {k} {e[k][:10]}" for k in ("started", "finished") if e.get(k))
            print(f"{mark}{aid}: {e.get('status', 'not registered')} — {title}{dates}")
        if not built and not entries:
            print("no adventures built yet (/solo-rpg-gm:ingest-adventure)")
        return 0
    if not a.id:
        sys.exit(f"give the adventure id: rpg-gm adventure {a.action} <id>")
    aid = a.id
    if aid not in built:
        sys.exit(f"adventure '{aid}' isn't built in this vault (built: {', '.join(built) or 'none'})")
    e = adventure_entry(cfg, aid)
    if a.action == "start":
        prev = cfg.get("active_adventure")
        if prev and prev != aid:
            adventure_entry(cfg, prev)["status"] = PAUSED
            print(f"{prev}: paused")
        e["status"] = ACTIVE
        e.setdefault("started", now())
        e.pop("finished", None)  # restarting a finished or abandoned adventure reopens it
        cfg["active_adventure"] = aid
        gm_dir(aid).mkdir(parents=True, exist_ok=True)
        if not (gm_dir(aid) / "state.yaml").exists():
            save_state(aid, new_state(aid))
            log_change(aid, "start", "", None, "new state")
            print(f"{aid}: new state, current = {new_state(aid)['current']}")
        if not (gm_dir(aid) / "canon.md").exists():
            (gm_dir(aid) / "canon.md").write_text(CANON_HEADER.format(aid=aid), encoding="utf-8")
        print(f"{aid}: active")
    else:  # finish | abandon
        e["status"] = "finished" if a.action == "finish" else "abandoned"
        e["finished"] = now()
        if cfg.get("active_adventure") == aid:
            cfg["active_adventure"] = None
        print(f"{aid}: {e['status']}")
    save_cfg(cfg)
    return 0


def cmd_set_session(a) -> int:
    cfg = load_cfg()
    cfg["current_session"] = a.path
    save_cfg(cfg)
    print(f"current_session = {a.path}")
    return 0


# ---------------------------------------------------------------- state commands

def cmd_state(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    st = load_state(aid)
    if a.action == "show":
        val = get_path(st, a.path) if a.path else st
        print(yaml.safe_dump(val, sort_keys=False, allow_unicode=True).rstrip() if isinstance(val, (dict, list))
              else short(val))
        return 0
    if not a.path or a.value is None:
        sys.exit("usage: rpg-gm state set <path> <value> [--why TEXT]   (value 'null' removes the key)")
    value = yaml.safe_load(a.value)
    old = set_path(st, a.path, value)
    save_state(aid, st)
    log_change(aid, "set", a.path, old, value, a.why or "")
    print(f"{a.path}: {short(old)} → {short(value)}")
    return 0


def cmd_enter(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    locs = [str(x) for x in (manifest(aid).get("elements") or {}).get("locations") or []]
    if a.loc not in locs:
        sys.exit(f"{a.loc} is not a location in {aid}")
    st = load_state(aid)
    old = st.get("current")
    st["current"] = a.loc
    seen = (st.setdefault("elements", {})).get(a.loc)
    if seen is None:
        st["elements"][a.loc] = "entered"
    save_state(aid, st)
    log_change(aid, "enter", "current", old, a.loc, a.why or "")
    print(f"current: {short(old)} → {a.loc}  ({'first visit' if seen is None else f'visited before: {seen}'})")
    return 0


def _roll_sealed(expr: str, label: str = "gm check"):
    common, dice = core()
    r = dice.roll(str(expr))
    rec = r.to_dict()
    rec["label"] = label
    common.seal({"type": "roll", **rec}, label)
    return r.total


def cmd_spawn(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    mode = cfg.get("party_mode", "as-written")
    if mode != "as-written":
        print(f"warning: party_mode '{mode}' isn't implemented yet; spawning as written", file=sys.stderr)
    f = gp.adventure_dir(ROOT, aid) / "stat-blocks" / f"{a.stat}.yaml"
    if not f.exists():
        sys.exit(f"no stat block {a.stat} in {aid}")
    sb = load_yaml(f) or {}
    st = load_state(aid)
    at = a.at or st.get("current")
    count_expr = a.count or "1"
    try:
        count = int(count_expr)
    except ValueError:
        count = _roll_sealed(count_expr)
    fields = sb.get("fields") or {}
    fixed_hp = fields.get("hp", sb.get("hp"))
    insts = st.setdefault("instances", {})
    n = 1
    made = []
    for _ in range(max(0, count)):
        while f"{a.stat}#{n}" in insts:
            n += 1
        iid = f"{a.stat}#{n}"
        if isinstance(fixed_hp, int):
            hp = fixed_hp
        elif sb.get("hp_roll"):
            hp = _roll_sealed(sb["hp_roll"])
        else:
            hp = None
        insts[iid] = {"at": at, "hp": hp, "max_hp": hp, "status": "active"}
        made.append(f"{iid} (hp {short(hp)})")
        log_change(aid, "spawn", f"instances.{iid}", None, insts[iid], a.why or "")
    save_state(aid, st)
    print(f"spawned at {at}: {', '.join(made) or 'none'}")
    return 0


def cmd_damage(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    st = load_state(aid)
    inst = (st.get("instances") or {}).get(a.instance)
    if inst is None:
        sys.exit(f"no instance {a.instance} (spawn it first)")
    if inst.get("hp") is None:
        sys.exit(f"{a.instance} has no hit points recorded; set them with rpg-gm state set")
    old = inst["hp"]
    new = old - a.amount
    if inst.get("max_hp") is not None and a.amount < 0:
        new = min(new, inst["max_hp"])
    inst["hp"] = new
    status = inst.get("status")
    if new <= 0 and status == "active":
        inst["status"] = "down"
    save_state(aid, st)
    log_change(aid, "damage", f"instances.{a.instance}.hp", old, new, a.why or "")
    extra = f", status {status} → {inst['status']}" if inst["status"] != status else ""
    print(f"{a.instance}: hp {old} → {new}{extra}")
    return 0


def cmd_tick(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    clocks = {str(c.get("id")): c for c in manifest(aid).get("clocks") or []}
    if a.clock not in clocks:
        sys.exit(f"no clock {a.clock} in {aid} (clocks: {', '.join(clocks) or 'none'})")
    st = load_state(aid)
    mx = int(clocks[a.clock].get("max", 0))
    old = int((st.setdefault("clocks", {})).get(a.clock, 0))
    new = max(0, min(mx, old + a.n))
    st["clocks"][a.clock] = new
    save_state(aid, st)
    log_change(aid, "tick", f"clocks.{a.clock}", old, new, a.why or "")
    line = f"{a.clock}: {old} → {new} / {mx}"
    if new >= mx:
        evs = []
        for p in sorted((gp.adventure_dir(ROOT, aid) / "events").glob("*.md")):
            t = p.read_text(encoding="utf-8")
            if t.startswith("---"):
                fm = yaml.safe_load(t[3:t.find("\n---", 3)]) or {}
                if str(fm.get("clock")) == a.clock:
                    evs.append(p.stem)
        line += f"  FULL → {', '.join(evs) or 'no event names this clock'}"
    print(line)
    return 0


def cmd_canon(a) -> int:
    cfg = load_cfg()
    aid = resolve_adv(cfg, a.adv)
    p = gm_dir(aid) / "canon.md"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(CANON_HEADER.format(aid=aid), encoding="utf-8")
    session = Path(cfg.get("current_session") or "no session").stem
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- [{now()}] ({session}) {a.fact} — basis: {a.basis}\n")
    n = sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.startswith("- ["))
    print(f"canon {aid}: {n} entr{'y' if n == 1 else 'ies'}")
    return 0


# ---------------------------------------------------------------- reveal

def cmd_reveal(a) -> int:
    cfg = load_cfg()
    aid = a.id or cfg.get("active_adventure")
    if not aid:
        sys.exit("give the adventure id")
    e = adventure_entry(cfg, aid)
    if e.get("status") not in ("finished", "abandoned") and not a.force:
        sys.exit(f"{aid} is {e.get('status')}: revealing it would spoil it. "
                 "Finish or abandon it first, or pass --force if the player insists.")
    d = gp.adventure_dir(ROOT, aid)
    m = manifest(aid)
    print(f"# Reveal: {aid} — {m.get('title')}\n")

    common, _ = core()
    import sealed  # type: ignore  (core/scripts is on sys.path via core())
    print("## Sealed rolls")
    root = common.find_campaign() or ROOT
    sealed.cmd_verify(root)
    print()
    sealed.cmd_show(root, since=e.get("started", ""), until=e.get("finished", ""))

    st_path = gm_dir(aid) / "state.yaml"
    st = (load_yaml(st_path) or {}) if st_path.exists() else {}
    seen = st.get("elements") or {}
    print("\n## Never reached or met")
    missed = 0
    for t, ids in (m.get("elements") or {}).items():
        if t not in ("locations", "npcs", "clues", "scenes", "items", "handouts"):
            continue
        for eid in ids or []:
            s = seen.get(eid)
            if s is None or (isinstance(s, dict) and not s.get("met", True)):
                missed += 1
                f = d / t / f"{eid}.md"
                title = "?"
                if f.exists():
                    txt = f.read_text(encoding="utf-8")
                    fm = yaml.safe_load(txt[3:txt.find("\n---", 3)]) if txt.startswith("---") else {}
                    title = (fm or {}).get("title", "?")
                print(f"- {eid} ({t}): {title}")
    if not missed:
        print("- nothing: the party saw it all")

    canon = gm_dir(aid) / "canon.md"
    print("\n## Canon (improvised facts)")
    lines = [ln for ln in canon.read_text(encoding="utf-8").splitlines() if ln.startswith("- [")] \
        if canon.exists() else []
    print("\n".join(lines) or "- none")

    audit = d / "AUDIT.md"
    print(f"\n## Build audit\n{audit if audit.exists() else 'no AUDIT.md'}")
    if audit.exists():
        for ln in audit.read_text(encoding="utf-8").splitlines()[:3]:
            print(ln)
    return 0


# ---------------------------------------------------------------- argparse

def add_parsers(sub) -> Dict[str, Any]:
    def adv(p):
        p.add_argument("--adv", help="adventure id (default: the active adventure)")
        return p

    p = sub.add_parser("adventure", help="list, start, finish or abandon adventures")
    p.add_argument("action", choices=["list", "start", "finish", "abandon"])
    p.add_argument("id", nargs="?")
    p = sub.add_parser("set-session", help="record the current session note")
    p.add_argument("path")
    p = adv(sub.add_parser("state", help="show or change hidden state"))
    p.add_argument("action", choices=["show", "set"])
    p.add_argument("path", nargs="?", help="dotted path, e.g. elements.loc-05 or instances.stat-02#1.status")
    p.add_argument("value", nargs="?", help="YAML value; 'null' removes the key")
    p.add_argument("--why", default="")
    p = adv(sub.add_parser("enter", help="the party moves to a location"))
    p.add_argument("loc")
    p.add_argument("--why", default="")
    p = adv(sub.add_parser("spawn", help="put stat-block instances in play"))
    p.add_argument("stat")
    p.add_argument("--count", help="number or dice expression (rolled secretly)")
    p.add_argument("--at", help="location (default: current)")
    p.add_argument("--why", default="")
    p = adv(sub.add_parser("damage", help="damage (or, negative, heal) an instance"))
    p.add_argument("instance")
    p.add_argument("amount", type=int)
    p.add_argument("--why", default="")
    p = adv(sub.add_parser("tick", help="advance a clock"))
    p.add_argument("clock")
    p.add_argument("n", nargs="?", type=int, default=1)
    p.add_argument("--why", default="")
    p = adv(sub.add_parser("canon", help="record an improvised fact"))
    p.add_argument("fact")
    p.add_argument("--basis", required=True, help="why it's true: 'minor detail', or the oracle question, likelihood and result")
    p = sub.add_parser("reveal", help="after an adventure: sealed rolls, what was missed, canon, audit")
    p.add_argument("id", nargs="?")
    p.add_argument("--force", action="store_true")
    return {"adventure": cmd_adventure, "set-session": cmd_set_session, "state": cmd_state,
            "enter": cmd_enter, "spawn": cmd_spawn, "damage": cmd_damage, "tick": cmd_tick,
            "canon": cmd_canon, "reveal": cmd_reveal}


def run(cmd: str, a, root: Path, handlers: Dict[str, Any]) -> int:
    global ROOT
    ROOT = root
    os.chdir(root)  # core's seal() finds the campaign from the working directory
    return handlers[cmd](a)
