---
name: roll
description: Roll dice for solo RPG play with the auditable rpg-roll script. Use this whenever any dice roll is needed during play, whether the player asks for one ("roll 2d6", "make a check", "roll for initiative") or a rule or procedure step calls for one. Never produce a die result any other way.
argument-hint: "[expression] [--check '>=N'] [--label text]"
allowed-tools: Bash(rpg-roll *)
---

# Rolling dice

Every number that claims to come from a die must come from `rpg-roll`. The script draws from
OS entropy and writes each result to the campaign audit trail (`.solo-rpg/audit.jsonl`), so the
record can be trusted later. A number Claude "rolls" itself is a fabricated result and has no
place in the record.

## How

```
rpg-roll <expression> [more expressions] [--times N] [--label "what for"] [--check ">=8"] [--log "<session note>"]
```

- Always pass `--label` with the purpose, such as the character, skill or procedure step.
- During a session, pass `--log` with the current session note so the line lands in the log.
  The session skills say which note is current. If none is known, ask once.
- `--check` compares the total against a target and prints PASS/FAIL. Use it only when the
  rules define the comparison, and take the comparison direction from the rules
  (roll-over or roll-under).
- `rpg-roll --help-notation` shows the full notation: keep/drop (`4d6kh3`), exploding (`!`),
  success pools (`6d10>=8`), rerolls (`r<2`), digit dice (`d66`), percentile (`d%`), fudge (`dF`).

`$ARGUMENTS`, if present, is the expression the player asked for.

## Reporting

Quote the script's result line exactly, then add the rules consequence only if the rules
determine it, with a citation. Examples: "PASS, margin +2 → Effect 2 [p.N]", or
"a 1 is always a failure [p.N]". Stop there. What the result means in the fiction is up to
the player.

If the script errors, show the error and fix the expression. Do not guess a result.
If the player rolled physical dice, record their number with a `(player roll)` note instead.
