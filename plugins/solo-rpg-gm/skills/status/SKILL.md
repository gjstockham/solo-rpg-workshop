---
name: status
description: Show the party's status in a solo-rpg-gm (GM-style) campaign from the player's own notes only - characters, what the party knows, open leads and the current session. Use when the player asks "where are we", "how is the party", "what do we know" or "what were we doing", in a GM-style vault.
argument-hint: "[character, or 'known', 'leads']"
allowed-tools:
  - Bash(rpg-gm status)
---

# Party status

**Player-known only.** Read the vault's notes, never `.solo-rpg/`, never `rpg-gm state`:
this is what the party knows, not what the GM knows. Input: $ARGUMENTS.

From `solo-rpg.yaml` → `paths`, report briefly:
- **Party**: each character's key sheet values (hit points, resources, conditions) from the
  characters folder, with any who are dead or missing.
- **Where**: the party's position as the last session note puts it.
- **Known**: `Known/` entries for the current adventure with `status: current`, grouped by
  kind; `outdated` ones only if asked.
- **Leads**: clues and rumours not yet followed up, as the notes record them.
- **Session**: the current session note, and the adventure (`rpg-gm status` for its id,
  title and status).

If $ARGUMENTS names a character or a section, show just that, in more detail. Don't add
anything the notes don't say.
