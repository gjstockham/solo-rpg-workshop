---
name: vault-setup
description: Set up or extend an Obsidian campaign vault for solo play with one or more solo-rpg modules. Designs the folders, note templates, frontmatter, Dataview dashboards, campaign config and CLAUDE.md play contract, enables only this campaign's module plugins, and recommends community plugins. Use when the player starts a new campaign, adds a module to an existing one, or wants their vault reorganised around the rules.
argument-hint: "[campaign name] [module ids...]"
disable-model-invocation: true
allowed-tools:
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/*)
---

# Set up a campaign vault

Run from the vault root (the folder containing `.obsidian/`). Input: $ARGUMENTS.
Never touch `.obsidian/`. Obsidian plugin installation and settings are the player's job.

This runs after at least one module has been built here with `/solo-rpg-forge:ingest` and
`/solo-rpg-forge:build-module`, because the vault structure is designed from the module
manifests.

## 1. Gather

- `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault_tool.py" modules` lists the modules already
  built in this vault, with their records, trackers, lists and procedures. If it reports
  none, the player needs `/solo-rpg-forge:ingest` first.
  Confirm the campaign name and module set with the player. A game module usually pairs with
  a solo-engine module. Honour `requires:`.
- Survey what the vault already has: folders, existing notes, templates, and any frontmatter
  conventions (grep a few notes). **An existing vault is the player's structure. Adapt to it**
  and map module concepts onto the existing folders rather than imposing new ones.
  If `solo-rpg.yaml` exists, this is an extension: add to it, don't restart.
- Ask the player's preferences in **one** message, with defaults offered:
  - Scene notes: separate notes per scene, or scenes as headings inside the session note
    (default: headings).
  - Dashboards: Dataview (default) or core Bases.
  - Folder style: flat by type (default), or nested under a campaign folder, for vaults
    holding several campaigns.

## 2. Propose

Present the plan as a tree plus a short table. **Wait for approval before writing anything.**

- **Folders**: one per record type and list from the manifests, plus Sessions, Templates,
  Dashboards, and Reference (optional).
- **Templates**: one per record type, list item and session, using the frontmatter below.
- **`Campaign.md`**: campaign-scoped trackers as frontmatter, active modules, and links to
  the dashboards and house rules.
- **`House Rules.md`**: dated rulings and house rules. The rules lawyer checks it.
- **Dashboards**: open lists (such as threads), records by status, and recent sessions.
- **Community plugins**: from `${CLAUDE_PLUGIN_ROOT}/references/obsidian-plugins.md`, only
  what the modules call for, each with a one-line reason. Suggest searching for a
  system-specific plugin, and agree on a division of labour if one exists.

### Frontmatter conventions
- Every note gets `type: <record-type|list-id|session|campaign>`. Dashboards key on this.
- Records and list items get `status` (e.g. `active | resolved | dead | removed`, or the
  module's own states) and `tags` if the player uses them.
- Record fields come from `records[].fields` in the manifest, with kebab-case names, typed
  defaults (number → the manifest default or 0; text → empty), and min/max in a trailing
  comment only if the template engine keeps comments. Otherwise put limits in the dashboard.
- Scene- or record-scoped trackers go on the note they belong to. Campaign-scoped trackers go in `Campaign.md`.
- A list item used for random picks can carry a `weight` if the rules weight entries
  (`rpg-table pick --dir <folder> --where status=active --weight weight`).
- Session notes carry `session: N`, `date`, `in-game-date` (if the module has a calendar) and `type: session`.

Templates must work as plain core Templates (`{{date}}`, `{{title}}`). Add Templater syntax
only if the player uses Templater.

## 3. Write (after approval)

1. Configuration (deterministic):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault_tool.py" init --campaign "<name>" --modules <ids...>
   ```
   This writes `solo-rpg.yaml`, creates `.solo-rpg/` (audit trail), and merges
   `.claude/settings.json` to allow `rpg-roll`/`rpg-table` and deny edits to `.obsidian/`
   and the audit trail. Use `--dry-run` first if the vault already has
   `.claude/settings.json`, and show the diff. If you changed folder names, update `paths:`
   in `solo-rpg.yaml`.
   `modules:` lists the campaign's active modules. A module skill present in the vault but
   not listed still loads, but the core scripts ignore its tables.
2. Folders, templates, `Campaign.md`, `House Rules.md` and dashboards, as approved.
3. **`CLAUDE.md`** at the vault root, under ~150 lines:
   - Title and one line on the campaign, plus the active modules and what each is for.
   - The full play contract: copy it from the solo-rpg-core plugin's
     `references/guardrails.md`. `vault_tool.py guardrails` prints its path.
   - Vault map: each folder and template → what goes there. Where the current session is
     recorded (`solo-rpg.yaml` → `current_session`). Where house rules live.
   - The frontmatter conventions above, concisely.
   - Any division of labour agreed with a system-specific Obsidian plugin.
   - "Session commands: see `.claude/skills/`" (filled in by session-kit).
   If a CLAUDE.md already exists, merge into it under clear headings rather than overwriting.
4. **`.claude/agents/rules-lawyer.md`**: a vault-specific copy of the core `rules-lawyer`
   agent (project agents take precedence over plugin ones), naming this campaign's modules
   and the exact paths to their `reference/rules/` folders and the house-rules note, so it
   doesn't have to search for them. Keep its cite-or-abstain contract word for word; only
   the "Where the rules are" section changes. Skip this if the player already has their own
   `rules-lawyer` agent, and say so.
5. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault_tool.py" status` and show the result.

## 4. Hand-off

List what was created and which community Obsidian plugins to install. Tell the player to
**restart Claude Code**: `.claude/agents/` is only read at launch, so the new rules-lawyer
agent won't load until they do. (Skills under `.claude/skills/` are watched and need no
restart, unless that directory was created during this session.) Suggest
`/solo-rpg-forge:session-kit` next.
