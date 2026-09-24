"""Dice expression parser and roller for solo-rpg-core.

All randomness comes from secrets.SystemRandom (OS entropy) unless a seed is
given for testing. Nothing here knows about any particular game.

Grammar (whitespace ignored, case-insensitive):

    expr    := term (('+' | '-') term)*
    term    := dice | integer
    dice    := [count] 'd' sides modifier*
    sides   := integer | '%' | 'F'
    modifier:= 'kh'N | 'kl'N | 'dh'N | 'dl'N      keep/drop highest/lowest
             | '!' [cmp N]                          explode (default: on max)
             | 'r' cmp N                            reroll once when cmp matches
             | cmp N                                count successes (>=, <=, >, <, =)

Digit-concatenation dice: a die size made of 2-3 repeated digits from 2-9
(d66, d666, d88, d44 ...) is read one die per digit, concatenated, e.g.
d66 -> first d6 is tens, second d6 is units -> 11..66. Use d100 / d% for
percentile. A count before a concatenation die rolls it that many times and
sums (rarely wanted).
"""
from __future__ import annotations

import random
import re
import secrets
from dataclasses import dataclass, field
from typing import List, Optional

MAX_EXPLOSIONS = 100
_rng: random.Random = secrets.SystemRandom()


def set_seed(seed: Optional[int]) -> None:
    """Seed only for tests; normal play uses OS entropy."""
    global _rng
    _rng = random.Random(seed) if seed is not None else secrets.SystemRandom()


def rand_int(lo: int, hi: int) -> int:
    return _rng.randint(lo, hi)


class DiceError(ValueError):
    pass


_CMP = r"(>=|<=|>|<|=)"


def _cmp(op: str, a: int, b: int) -> bool:
    return {">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b, "=": a == b}[op]


@dataclass
class TermResult:
    text: str                # the term as written
    value: int               # contribution before sign
    sign: int = 1
    rolls: List[int] = field(default_factory=list)   # every die face rolled
    kept: List[int] = field(default_factory=list)    # faces that counted
    note: str = ""           # e.g. "3 successes", "exploded x2"

    def describe(self) -> str:
        if not self.rolls:
            return str(self.value)
        if self.kept:
            s = f"{self.rolls} keep {self.kept}"
        else:
            s = f"{self.rolls}"
        if self.note:
            s += f" ({self.note})"
        return s


@dataclass
class RollResult:
    expression: str
    total: int
    terms: List[TermResult]
    kind: str = "sum"        # "sum" or "successes"

    def breakdown(self) -> str:
        parts = []
        for i, t in enumerate(self.terms):
            sign = "" if i == 0 and t.sign > 0 else (" + " if t.sign > 0 else " - ")
            if i == 0 and t.sign < 0:
                sign = "-"
            parts.append(f"{sign}{t.describe()}")
        return "".join(parts)

    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "total": self.total,
            "kind": self.kind,
            "terms": [
                {"text": t.text, "sign": t.sign, "value": t.value,
                 "rolls": t.rolls, "kept": t.kept, "note": t.note}
                for t in self.terms
            ],
        }


_TERM_RE = re.compile(r"[+-]?[^+-]+")
_DICE_RE = re.compile(r"^(\d*)d(\d+|%|f)(.*)$", re.I)


def _is_concat(sides: str) -> bool:
    return (sides.isdigit() and 2 <= len(sides) <= 3 and len(set(sides)) == 1
            and sides[0] in "23456789")


def _split_terms(expr: str) -> List[str]:
    e = expr.replace(" ", "")
    if not e:
        raise DiceError("empty expression")
    # modifiers like 'r<2' or '>=5' contain no +/-; negative literals are not allowed there
    terms = _TERM_RE.findall(e)
    if "".join(terms) != e:
        raise DiceError(f"could not parse '{expr}'")
    return terms


def _parse_mods(mods: str):
    out = []
    pos = 0
    pat = re.compile(r"(kh|kl|dh|dl)(\d+)|!(?:" + _CMP + r"(\d+))?|r" + _CMP + r"(\d+)|" + _CMP + r"(\d+)", re.I)
    while pos < len(mods):
        m = pat.match(mods, pos)
        if not m:
            raise DiceError(f"unknown dice modifier '{mods[pos:]}'")
        g = m.groups()
        if g[0]:
            out.append((g[0].lower(), int(g[1])))
        elif m.group(0).startswith("!"):
            out.append(("!", g[2] or None, int(g[3]) if g[3] else None))
        elif m.group(0).lower().startswith("r"):
            out.append(("r", g[4], int(g[5])))
        else:
            out.append(("count", g[6], int(g[7])))
        pos = m.end()
    return out


def _roll_die(sides: str) -> int:
    if sides == "%":
        return rand_int(1, 100)
    if sides == "f":
        return rand_int(-1, 1)
    if _is_concat(sides):
        d = int(sides[0])
        digits = [str(rand_int(1, d)) for _ in sides]
        _roll_die.last_digits = ",".join(digits)  # type: ignore[attr-defined]
        return int("".join(digits))
    n = int(sides)
    if n < 1:
        raise DiceError("dice need at least 1 side")
    return rand_int(1, n)


def _max_face(sides: str) -> int:
    if sides == "%":
        return 100
    if sides == "f":
        return 1
    return int(sides)


def _roll_dice_term(count: int, sides: str, mods) -> TermResult:
    if count < 1 or count > 1000:
        raise DiceError("dice count must be 1..1000")
    rolls: List[int] = []
    notes = []
    faces: List[int] = []
    explode = next((m for m in mods if m[0] == "!"), None)
    reroll = next((m for m in mods if m[0] == "r"), None)
    if explode and (_is_concat(sides) or sides == "f"):
        raise DiceError("exploding is not supported on concatenation or fudge dice")
    explosions = 0
    for _ in range(count):
        v = _roll_die(sides)
        if _is_concat(sides):
            notes.append(f"digits {_roll_die.last_digits}")  # type: ignore[attr-defined]
        if reroll and _cmp(reroll[1], v, reroll[2]):
            old = v
            v = _roll_die(sides)
            notes.append(f"rerolled {old}->{v}")
        rolls.append(v)
        total_face = v
        if explode:
            op, n = (explode[1], explode[2]) if explode[1] else (">=", _max_face(sides))
            while _cmp(op, v, n) and explosions < MAX_EXPLOSIONS:
                v = _roll_die(sides)
                rolls.append(v)
                total_face += v
                explosions += 1
        faces.append(total_face)
    if explosions:
        notes.append(f"exploded x{explosions}")
    kept = list(faces)
    for m in mods:
        if m[0] in ("kh", "kl", "dh", "dl"):
            n = m[1]
            s = sorted(kept, reverse=True)
            if m[0] == "kh":
                chosen = s[:n]
            elif m[0] == "kl":
                chosen = s[-n:] if n else []
            elif m[0] == "dh":
                chosen = s[n:]
            else:
                chosen = s[:len(s) - n] if n else s
            # preserve original order for readability
            pool = list(chosen)
            kept = []
            for f in faces:
                if f in pool:
                    kept.append(f)
                    pool.remove(f)
    count_mod = next((m for m in mods if m[0] == "count"), None)
    if count_mod:
        succ = sum(1 for f in kept if _cmp(count_mod[1], f, count_mod[2]))
        notes.append(f"{succ} success{'es' if succ != 1 else ''} on {count_mod[1]}{count_mod[2]}")
        value = succ
    else:
        value = sum(kept)
    has_keep = any(m[0] in ("kh", "kl", "dh", "dl") for m in mods)
    tr = TermResult(text="", value=value, rolls=rolls, kept=kept if has_keep else [],
                    note=", ".join(dict.fromkeys(notes)))
    tr._is_count = bool(count_mod)  # type: ignore[attr-defined]
    return tr


def roll(expression: str) -> RollResult:
    terms_txt = _split_terms(expression)
    terms: List[TermResult] = []
    kind = "sum"
    for raw in terms_txt:
        sign = -1 if raw.startswith("-") else 1
        body = raw.lstrip("+-").lower()
        if body.isdigit():
            terms.append(TermResult(text=raw, value=int(body), sign=sign))
            continue
        m = _DICE_RE.match(body)
        if not m:
            raise DiceError(f"could not parse term '{raw}'")
        count = int(m.group(1)) if m.group(1) else 1
        sides = m.group(2).lower()
        mods = _parse_mods(m.group(3))
        tr = _roll_dice_term(count, sides, mods)
        tr.text, tr.sign = raw, sign
        if getattr(tr, "_is_count", False):
            kind = "successes"
        terms.append(tr)
    total = sum(t.sign * t.value for t in terms)
    return RollResult(expression=expression.strip(), total=total, terms=terms, kind=kind)


# ---------- static analysis used by table validation ----------

def possible_values(expression: str) -> Optional[List[int]]:
    """Every total the expression can produce, or None if too complex.

    Supports sums of plain NdX / d% / concatenation dice and integer constants.
    Keep/drop, explode, reroll and success-counting return None (use min/max
    checks instead).
    """
    totals = {0}
    for raw in _split_terms(expression):
        sign = -1 if raw.startswith("-") else 1
        body = raw.lstrip("+-").lower()
        if body.isdigit():
            totals = {t + sign * int(body) for t in totals}
            continue
        m = _DICE_RE.match(body)
        if not m or m.group(3):
            return None
        count = int(m.group(1)) if m.group(1) else 1
        sides = m.group(2).lower()
        if sides == "%":
            faces = range(1, 101)
        elif sides == "f":
            faces = range(-1, 2)
        elif _is_concat(sides):
            d = int(sides[0])
            faces_list = [0]
            for _ in sides:
                faces_list = [f * 10 + x for f in faces_list for x in range(1, d + 1)]
            faces = faces_list
        else:
            faces = range(1, int(sides) + 1)
        faces = list(faces)
        for _ in range(count):
            totals = {t + sign * f for t in totals for f in faces}
            if len(totals) > 100000:
                return None
    return sorted(totals)


def check(total: int, spec: str) -> bool:
    m = re.fullmatch(_CMP + r"\s*(-?\d+)", spec.strip())
    if not m:
        raise DiceError(f"bad check '{spec}', use e.g. '>=8' or '<=45'")
    return _cmp(m.group(1), total, int(m.group(2)))
