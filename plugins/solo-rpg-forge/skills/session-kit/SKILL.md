---
name: session-kit
description: Generate campaign-specific session-play skills in an Obsidian campaign vault by composing the procedures of its active solo-rpg modules (e.g. a game plus a solo engine) into start-session, scene, end-session and recap commands. Use after vault-setup, after adding or changing a module, or when the player wants to change how their sessions run.
argument-hint: "[optional: changes to the session flow]"
disable-model-invocation: true
allowed-tools:
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(rpg-table *)
---

# Build the session kit

Run from a vault that has `solo-rpg.yaml`. Input: $ARGUMENTS.

Output: a few more **project skills** in `<vault>/.claude/skills/` that run this campaign's
sessions, plus a composed `.claude/session-loop.md` that they share. The flow depends on the
combination of modules and on the player's own habits, so these are generated per vault
rather than shipped.

They sit alongside the module skills already in `.claude/skills/`, so check the directory
first and don't clobber a module or a skill of the player's own.

## 1. Read

- `solo-rpg.yaml`, the vault `CLAUDE.md`, and `vault_tool.py modules <active ids>` for the manifests.
- Every procedure file for `when` values `session-start`, `scene`, `encounter`, `downtime`,
  `session-end` and `on-demand` (in each module's `reference/procedures/`).
- The templates and folders the vault actually uses.

## 2. Compose the loop

Write `.claude/session-loop.md`: the campaign's play loop as numbered phases. Each step either
**calls** a module procedure by `<module-id>/<procedure-id>` or is a step-tagged line
(module-spec §4, tags CHOICE/ROLL/TABLE/RULE/RECORD/BRANCH) with `[module p.N]` citations.

Where modules overlap, don't guess. Common overlaps:
- Both a game and a solo engine define how scenes open or how questions are answered.
- Two modules track similar state, such as two different "tension" style trackers.
- Two modules treat the end of a session differently.

List each overlap and ask the player which module governs it, or how the two combine. Record
the answers in the loop file under `## Integration decisions` with the date. These are
house-rule-level choices, so add a line to `House Rules.md` as well.

Apply $ARGUMENTS (the player's requested changes) on top.

## 3. Generate skills

Create these in `.claude/skills/<name>/SKILL.md`. Short names are fine, but check
`ls .claude/skills` first: the module skills live there too.

| Skill | Invocation | Does |
|---|---|---|
| `session-start` | player only | Create the session note from the template (next number); set `current_session` in `solo-rpg.yaml`; run the session-start phase: recap from the last session note's **recorded** content, open lists, tracker values, start-of-session procedures |
| `scene` | player only | Run one pass of the scene phase: the scene-opening procedure(s) and their rolls, logged under a new scene heading (or a new scene note). Takes the player's scene setup as $ARGUMENTS |
| `ask` | player only | Answer a yes/no or open question with the governing oracle procedure; log question + result verbatim. **No interpretation** |
| `session-end` | player only | Run the session-end phase: propose all RECORD changes as a list, apply after confirmation; close the session note |
| `recap` | player only | Summarise recorded events from the last N sessions (default 1) strictly from the notes, quoting the player's own wording where possible |
| `status` | model + player | Current trackers, open lists and active records (read-only) |

Every generated skill must:
- Start with: "Follow the play contract in CLAUDE.md. The player is the GM. Report results; do not invent content."
- Reference `.claude/session-loop.md` for the steps, rather than duplicating them.
- Use `rpg-roll` and `rpg-table` with `--label` and `--log "<current_session>"`.
- Stop at every [CHOICE].
- Carry `disable-model-invocation: true`, except `status`, and an `argument-hint`.

Module procedures that the player may call directly already have runner skills
(`/<module-id>-<procedure-id>`). Don't duplicate them. Mention them in the CLAUDE.md
"Session commands" section instead.

## 4. Update CLAUDE.md

Replace the "Session commands" section with a table: command, when to use it, and what it
logs. Include the module procedure skills and the core ones (`/solo-rpg-core:rules`,
`/solo-rpg-core:interpret`).

## 5. Dry run

With the player's permission, walk through `session-start` using clearly marked test rolls
(`--seed 1`, which the scripts tag `[SEEDED TEST ROLL]`) into a scratch note
`Sessions/_kit-test.md`. Check that every referenced table and procedure resolves. Then
delete that scratch note, since it was test output Claude created in this run. Report any
fixes you made.
