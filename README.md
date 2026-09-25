# solo-rpg-workshop

A Claude Code plugin marketplace for solo tabletop RPG play in Obsidian, where Claude acts
strictly as **record-keeper, dice box, table reader and rules lawyer**. Claude is never the GM.

| Plugin | What it is |
|---|---|
| `solo-rpg-core` | `rpg-roll` and `rpg-table` (on PATH while enabled), skills `roll`, `table`, `record`, `rules`, `interpret`, the `rules-lawyer` agent, and the play contract |
| `solo-rpg-forge` | The builder: `ingest` → `build-module` turn a rulebook PDF into a **module plugin**; `vault-setup` and `session-kit` build a campaign vault around one or more modules |

You install this marketplace once. The forge then writes everything it builds **into your own
folders, never into this repo or the plugin cache**:

| What | Where it's built |
|---|---|
| Ruleset modules (rules, tables, procedures, skills) | Your **module library**: a folder you choose that becomes your own private local marketplace |
| Campaign config, templates, dashboards, `CLAUDE.md`, session skills | Your **campaign vault**: `.claude/skills/`, `.claude/settings.json`, `solo-rpg.yaml` |

## Install (once)

1. Python 3.9+ and: `pip install pyyaml pdfplumber pypdf`
2. In Claude Code:
   ```
   /plugin marketplace add gjstockham/solo-rpg-workshop
   /plugin install solo-rpg-core@solo-rpg-workshop
   /plugin install solo-rpg-forge@solo-rpg-workshop
   ```
   Install them at **user** scope so they're available in every folder.
3. Check: `rpg-roll 2d6` inside Claude Code.

On Windows, the `bin/` wrappers are bash scripts, which Claude Code runs via Git Bash. If
`python3` resolves to the Microsoft Store stub, set `SOLO_RPG_PYTHON` to your real
interpreter path.

## Workflow

### 1. Build a module (once per book), in your library folder

```
mkdir ~/rpg-library && cd ~/rpg-library && claude
/solo-rpg-forge:ingest ~/books/mygame.pdf      # first run offers to make this folder your library
  (approve SURVEY.md)
/solo-rpg-forge:build-module <id>
  (proof-read plugins/<id>/VERIFY.md)
/plugin marketplace add ~/rpg-library          # once per library
/plugin install <id>@solo-rpg-library          # the name you gave the library
```

The first ingest runs `module_tool.py init`, which turns the current folder into a library:

```
~/rpg-library/
  .claude-plugin/marketplace.json   your marketplace (default name: solo-rpg-library)
  plugins/<module-id>/              built modules, registered automatically
  staging/<module-id>/              PDF extraction, SURVEY.md, BUILD-STATE.md (gitignored)
```

- Big books are resumable. `BUILD-STATE.md` tracks progress across sessions. Just re-run
  `build-module` from the library folder.
- Modules install **disabled**. Each vault enables only its own modules, so rules never leak
  between campaigns.
- Build solo engines and oracles as their own modules (`kind: solo-engine`), so the same one
  can be combined with any game.
- Put the library under git (privately). The modules you build are valuable.
- The library can be the vault itself if you only run one campaign. Obsidian will then show the
  rules files too.

### 2. Set up a campaign (once per vault), in your vault folder

```
cd <vault> && claude
/solo-rpg-forge:vault-setup "<campaign>" <module ids>   # asks for your library path if it's elsewhere
/solo-rpg-forge:session-kit
/session-start … /scene … /ask … /session-end
```

`vault-setup` records the library in `solo-rpg.yaml` (`library:`) and registers it in
`.claude/settings.json` (`extraKnownMarketplaces`). The core scripts use that entry to find
tables, and a fresh clone of the vault uses it to offer to install its modules.

### Finding the library

The forge and the core scripts look in this order:

1. The `SOLO_RPG_LIBRARY` environment variable (library folder).
2. `library:` in the campaign's `solo-rpg.yaml`.
3. The nearest folder at or above the working directory containing `.claude-plugin/marketplace.json`.

The forge scripts also take `--library <path>`.

## Trust model

- Every roll and table result is appended to `<vault>/.solo-rpg/audit.jsonl` by the scripts.
  Vault settings deny Claude edits to that folder and to `.obsidian/`.
- Tables are data. `rpg-table validate` proves there are no gaps or overlaps.
  `rpg-table verify-report` gives you a proof-reading checklist against the book, and
  `rpg-table mark-verified` records your sign-off.
- The rules lawyer cites printed pages, or says the loaded rules don't cover the question.
- Oracle interpretation happens only through `/solo-rpg-core:interpret`, when you ask.

## Copyright

Modules contain condensed and partly verbatim text from books you own. Keep your module
library **private**, and don't publish modules built from commercial books. This repo ships
only the tools and contains no book content.

## Developing this repo

```
.claude-plugin/marketplace.json
plugins/solo-rpg-core/     bin/ scripts/ skills/ agents/ references/
plugins/solo-rpg-forge/    scripts/ skills/ agents/ references/module-spec.md
```

To test local changes, add this checkout as a marketplace instead of the GitHub one
(`/plugin marketplace add <path to checkout>`). Run the forge from a separate scratch folder.
It refuses to build modules inside this repo.
