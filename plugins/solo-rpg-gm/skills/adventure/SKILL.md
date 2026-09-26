---
name: adventure
description: List, start, switch, finish or abandon adventures in a solo-rpg-gm (GM-style) campaign. Use when the player wants to see their adventures, begin or switch to another one, or mark one finished or abandoned.
argument-hint: "[list | start <id> | finish <id> | abandon <id>]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
---

# Adventures

Input: $ARGUMENTS (blank means `list`).

- **list**: `rpg-gm adventure list`. Titles, statuses and dates are fine to show.
- **start `<id>`** (also for switching): `rpg-gm adventure start <id>`; the current
  adventure is paused, with its state kept. Quote the new adventure's party guidance
  (`adventure.yaml` → `party`) and point out any mismatch with the current party. Then
  suggest `/solo-rpg-gm:start` to play.
- **finish `<id>`** / **abandon `<id>`**: confirm with the player, then
  `rpg-gm adventure finish|abandon <id>`. Update `Campaign.md`, and mark `Known/` entries
  for it `outdated` only if the player wants. Mention `/solo-rpg-gm:reveal` for seeing
  what they missed.
- A new adventure to add: `/solo-rpg-gm:ingest-adventure` and
  `/solo-rpg-gm:build-adventure`, then `rpg-gm init` registers it.
