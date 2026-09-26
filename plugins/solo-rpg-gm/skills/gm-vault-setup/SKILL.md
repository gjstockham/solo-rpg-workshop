---
name: gm-vault-setup
description: Set up an Obsidian vault for GM-style solo play, where Claude runs published adventures as GM with a forge-built rules module. Writes the campaign config, the GM play contract in CLAUDE.md, player-facing folders, templates and dashboards, a campaign rules lawyer, and installs the built-in GM oracle. Use when the player wants to start a GM-style campaign, or after adding an adventure or rules module to one.
argument-hint: "[campaign name] [rules module ids...]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
  - Bash(rpg-table *)
---

# Set up a GM-style vault

Run from the vault root (the folder containing `.obsidian/`). Input: $ARGUMENTS.
Never touch `.obsidian/`. Obsidian plugin installation and settings are the player's job.

This runs after the rules module has been built here with the forge. Adventures can be
built before or after; re-running this skill registers new ones.

**No spoilers.** Adventure titles are fine (the player chose them), but nothing from inside
an adventure module goes in any note or message.

## 1. Gather

- `rpg-gm status` and `rpg-gm where`: the campaign config (if any), rules modules and built
  adventures.
  - If `solo-rpg.yaml` exists **without** `style: gm`, this is a clerk-style campaign. Stop:
    GM play needs its own vault.
  - If it exists **with** `style: gm`, this is an extension (new adventure, new rules
    module, changed preferences). Keep what's there and add to it.
  - If there's no rules module, send the player to `/solo-rpg-forge:ingest` and
    `/solo-rpg-forge:build-module` for the rulebook first.
- Read each rules module's `module.yaml`: its `records` (the character sheet above all),
  `trackers` and `lists`, and its `procedures` (character creation especially).
- Survey what the vault already has: folders, notes, templates, frontmatter conventions.
  **An existing vault is the player's structure. Adapt to it.**
- Ask the player's preferences in **one** message, with defaults offered:
  - Campaign name and which rules module(s) it uses (default: the ones present).
  - Dashboards: Dataview (default) or core Bases.
  - Folder style: flat by type (default), or nested under a campaign folder.
  - The keeper's model: the keeper agent reads the adventure for the GM during play, often.
    Default: the same model as the session (`inherit`). A smaller, cheaper model (such as
    `sonnet` or `haiku`) costs less per session but may miss or muddle details. They can
    change it later in `.claude/agents/keeper.md`.

## 2. Propose

Present the plan as a tree plus a short table. **Wait for approval before writing
anything.** Everything here is player-facing; hidden material lives only under `.solo-rpg/`.

- **Folders**: `Characters/` (or the rules module's own folder for its character record),
  `Sessions/`, `Known/`, `Handouts/`, `Templates/`, `Dashboards/`. A folder for any other
  player-facing record or list the rules module defines (for example retainers or
  holdings). Nothing for adventure content: the party learns it through `Known/`.
- **Templates**:
  - one per player-facing record type, with fields from `records[].fields`;
  - a session note (`type: session`, `session: N`, `date`, `adventure: <id>`);
  - a Known entry (`type: known`, `kind: place | person | creature | clue | item | rumour`,
    `adventure: <id>`, `status: current | outdated`, `learned: <session>`). The body holds
    what the party learned, in the party's words;
  - a handout (`type: handout`, `adventure: <id>`, `found: <session>`).
- **`Campaign.md`**: campaign name, rules modules, the adventures and their status, the
  rules module's campaign-scoped trackers as frontmatter, and links to dashboards and house
  rules.
- **`House Rules.md`**: dated rulings and house rules. The rules lawyer checks it.
- **Dashboards**: the party (characters by status), what's known (by kind, current
  adventure first), recent sessions.
- **Community plugins**: from the forge's `references/obsidian-plugins.md` (the `forge:`
  line of `rpg-gm where`), only what suits GM play, each with a one-line reason. Skip
  plugins for stat blocks and GM-side combat tracking: Claude handles those in hidden
  state. Dice Roller rolls aren't in the audit trail; say so if the player wants it.

Frontmatter conventions: every note gets `type:`; records and Known entries get `status`;
kebab-case property names; record fields typed from the manifest. Templates must work as
plain core Templates (`{{date}}`, `{{title}}`); add Templater syntax only if the player
uses Templater.

## 3. Write (after approval)

1. **Configuration** (deterministic):
   ```
   rpg-gm init --campaign "<name>" --rules <rules-ids...>
   ```
   This writes `solo-rpg.yaml` (`style: gm`, the modules, the built adventures as
   `planned`, defaults for `party_mode`, `session_log` and `paths`), creates
   `.solo-rpg/gm/`, installs the `gm-oracle` module into `.claude/skills/`, and merges
   `.claude/settings.json` (allows `rpg-roll`, `rpg-table`, `rpg-gm` and `rpg-sealed
   verify`; denies Claude edits to `.obsidian/` and the audit, sealed and state logs). Use
   `--dry-run` first if the vault already has `.claude/settings.json`, and show the diff. If
   you changed folder names, update `paths:` in `solo-rpg.yaml` to match.
2. **Folders, templates, `Campaign.md`, `House Rules.md` and dashboards**, as approved.
3. **`CLAUDE.md`** at the vault root, under ~150 lines:
   - Title and one line on the campaign: GM style, the rules module(s), the adventures.
   - The full GM play contract: copy `references/gm-contract.md` from this plugin (the
     `gm plugin:` line of `rpg-gm where`) word for word.
   - Vault map: each player-facing folder and template → what goes there. Where the current
     session is recorded (`solo-rpg.yaml` → `current_session`) and where house rules live.
     A line saying that `.solo-rpg/` holds hidden GM material the player shouldn't browse.
   - The frontmatter conventions, concisely.
   - A play commands table: `/solo-rpg-gm:start`, `end`, `status`, `recap`, `challenge`,
     `adventure` and `reveal`, each with when to use it; `/solo-rpg-core:rules` for rules
     questions; and the rules module's character-creation and other procedure commands
     (`/<rules-id>-<procedure-id>`, whichever exist). Note that plain messages are the
     party's actions, and "OOC:" marks an out-of-character question.
   If a CLAUDE.md already exists, merge into it under clear headings rather than
   overwriting.
4. **`.claude/agents/rules-lawyer.md`**: a vault-specific copy of solo-rpg-core's
   `agents/rules-lawyer.md` (the `core:` line of `rpg-gm where`). Keep its cite-or-abstain
   contract word for word. Only the "Where the rules are" section changes: name this
   campaign's rules module(s) and `gm-oracle`, the exact paths to their `reference/rules/`
   folders and the house-rules note, and add: "Never read `.solo-rpg/`; it holds the
   adventure, which the player hasn't seen." Skip this if the player already has their own
   `rules-lawyer` agent, and say so.
5. **`.claude/agents/keeper.md`**: a copy of this plugin's `agents/keeper.md` with
   `model:` set to the player's choice. Otherwise word for word. If one exists, change only
   its `model:` line (and only if the player asked).
6. Run `rpg-gm status` and show the result.

## 4. Hand-off

List what was created and which community Obsidian plugins to install. Tell the player to
**restart Claude Code**: `.claude/agents/` (the rules lawyer and the keeper) is only read
at launch. (Skills under
`.claude/skills/`, including the new `gm-oracle`, are watched, unless that directory was
created during this session.)

Next steps: create the party with the rules module's character-creation command, guided by
the adventure's party guidance (`rpg-gm status` shows which adventures are registered;
the guidance is in each adventure's `adventure.yaml`, and it's safe to quote). Then
`/solo-rpg-gm:start`.
