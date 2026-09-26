---
name: record
description: Record-keeping conventions for solo RPG campaign vaults in Obsidian. Use whenever creating or updating campaign notes during or after play, such as characters, NPCs, locations, threads, lists, trackers, session logs, house rules and frontmatter, or when the player says "note that", "add X to the list", "update my sheet", "mark that thread resolved" or "log this".
user-invocable: false
---

# Keeping the record

The vault is the source of truth. Claude writes into it like a careful clerk. Every change
traces back to something the player said, a script result, or a rules procedure.

## Where things go

Read the vault's `CLAUDE.md` and `solo-rpg.yaml` for this campaign's folders, templates and
current session note. Don't guess paths. Create new notes from the matching template in the
templates folder so frontmatter stays consistent.

## Rules for edits

1. **Only record what happened.** Record the player's own words, script output, and rule
   consequences with citations. Do not add descriptive detail the player didn't give. A new
   NPC note holds the name and facts the player stated, and nothing else.
2. **Frontmatter is data.** Keep property names and types exactly as the template defines
   them (Dataview dashboards depend on them). Clamp trackers to the min and max stated in the
   module manifest. If a change would exceed a limit, report the rule instead of writing it.
3. **Report every edit in one line**, for example `✎ Threads/Find the cache.md: status open → resolved`.
   For bulk updates at session end, show the list of intended changes first and apply
   them after the player confirms.
4. **Session log format.** Append to the current session note in play order. Script lines
   come from `--log`. Player narration is quoted or summarised as the player phrased it.
   Rules notes carry `[p.N]`.
5. **Links.** Use `[[wikilinks]]` for any named record that has, or should have, a note.
   Create stubs only when the player agrees or the procedure says the list gains an entry.
6. **House rules and rulings** go in the campaign's house-rules note with the date and the
   question they settle, so the rules lawyer can apply them later.
7. **GM-style campaigns** (`style: gm` in `solo-rpg.yaml`): Claude is the GM, so what it
   told the characters in play counts as "what happened" alongside the player's words, and
   the GM contract in the vault CLAUDE.md governs. Player-visible notes still hold only
   what the party knows. Hidden material stays under `.solo-rpg/`.
8. **Never delete** notes or log lines. Mark items as resolved, removed or dead via
   frontmatter status instead, unless the player explicitly asks for a deletion.
