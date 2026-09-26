---
name: table
description: Roll on or look up random tables from installed ruleset modules with the rpg-table script, including oracle, encounter, event, generator and name tables. Use this whenever play calls for a table result, when the player names a table, asks "what tables are there for X", or rolled physical dice and needs the row. Never recite table contents from memory.
argument-hint: "[table-id] [--mod N] [--column C]"
allowed-tools: Bash(rpg-table *)
---

# Random tables

Tables live as validated data files inside the vault's module skills. `rpg-table` rolls the dice and
finds the row itself, so the answer is always the transcribed book text with its page reference.
Claude never paraphrases, picks, or "remembers" a table row.

## Find the table

```
rpg-table list --search <word>      # search ids and titles in the campaign's active modules
rpg-table show <id>                 # print the whole table, its notes and source page
```

When several tables could fit, list the candidates and let the player choose. Choosing a
table is a GM decision.

## Roll or look up

```
rpg-table roll <id> [--mod N] [--column C] [--times N] --label "why" --log "<session note>"
rpg-table lookup <id> <value> [--column C] --log "<session note>"     # player rolled physically
rpg-table pick --items A B C [--count N] --label "why"                # uniform pick from a list
rpg-table pick --dir <folder> --where status=open --label "why"       # pick from notes by frontmatter
```

- Apply modifiers with `--mod` only when the rules or the player specify them. Cite the
  modifier's source.
- Follow-on rolls (`then`, `reroll`) and inline dice (`{{1d6}}`) are resolved by the script.
  Report them in the order printed.
- Column tables need `--column` when the rules pick the column (for example by situation).
  Otherwise the script shows all columns, and the player decides.

## Reporting

Quote the result line(s) as printed. Do not add description, colour or interpretation.
If the player wants help turning a result into fiction, that is `/solo-rpg-core:interpret`,
used only on request.

`--gm` and `--secret` exist only for GM-style campaigns (the vault CLAUDE.md says which style
applies). In a clerk-style campaign never use them.

If a table is missing or errors, say so. Offer `rpg-table lookup` with a physical roll, or
note the gap for the module's README. Do not improvise a substitute table.
