# Obsidian plugins for solo play, by capability

Recommend plugins by what the module needs, not by habit. Plugin status changes over time,
so tell the player to confirm each one in Obsidian's Community Plugins browser (maintained,
compatible) before installing. Claude never installs or configures plugins itself, because
`.obsidian/` is off-limits to it.

## Always useful

| Need | Plugin | Notes |
|---|---|---|
| Lists and dashboards from frontmatter (threads, NPCs, open clues) | **Dataview** | The vault templates emit Dataview queries. The core **Bases** plugin can do table views without code, so offer it as an alternative if the player prefers that. |
| Note templates with dates, prompts, cursor placement | **Templater** | Templates are written to work as plain core Templates too. Templater only adds date and prompt helpers. |
| Edit trackers and fields in place (sliders, number inputs, toggles) | **Meta Bind** | Good for trackers declared in module.yaml, so the player can adjust them without Claude. |

## When the module has…

| Module feature | Plugin | Why |
|---|---|---|
| Tactical combat with initiative | **Initiative Tracker** | Turn order, HP and conditions tracking in the sidebar. |
| Creature or NPC stat blocks | **Fantasy Statblocks** | Renders stat blocks from YAML. The layout can be customised to the book's format. |
| Maps: hex, region, sector, dungeon | **Leaflet** (image maps with markers), **Excalidraw** (sketching) | Markers can link to location notes. |
| In-game calendar, dates, travel time, seasons | **Calendarium** | Custom calendars and events linked to notes. |
| Clocks, progress tracks, threads as a board | **Kanban** | Threads and quests by status column. Dataview can cover this too, so pick one. |
| Many procedure checklists | **Tasks** or core checkboxes | Only if the player likes ticking steps off in notes. |
| The player wants to roll in Obsidian too | **Dice Roller** | These rolls are **not** in the audit trail. Tell the player to use `rpg-roll`, or say "I rolled N" so Claude can log it as a player roll. |

## System-specific plugins

Some game systems have dedicated community plugins covering moves, oracles, character
sheets or assets. For the module being set up:

1. Suggest the player search the Community Plugins browser for the game's name.
2. If one exists, agree on a **division of labour** before building the vault. For example,
   the dedicated plugin owns the character sheet and its native rolls, and Claude stays
   clerk and rules lawyer and doesn't duplicate the sheet. Record the agreement in the vault
   CLAUDE.md, and adapt templates so both tools don't write the same fields.

## Avoid recommending
- Several plugins that do the same job (Dataview + Datacore + Bases dashboards at once).
- Plugins that rewrite frontmatter automatically (linters and auto-formatters on save),
  because they can fight Claude's edits. If the player already uses one, exclude the campaign
  folders from it.
