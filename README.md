# solo-rpg-workshop

A Claude Code plugin marketplace for solo tabletop RPG play in Obsidian, where Claude acts
strictly as **record-keeper, dice box, table reader and rules lawyer**. Claude is never the GM.

| Plugin | What it is |
|---|---|
| `solo-rpg-core` | `rpg-roll` and `rpg-table` (on PATH while enabled), skills `roll`, `table`, `record`, `rules`, `interpret`, the `rules-lawyer` agent, and the play contract |
| `solo-rpg-forge` | The meta layer: `ingest` → `build-module` turn a rulebook PDF into a **module plugin**; `vault-setup` and `session-kit` build a campaign vault around one or more modules |
| *(your modules)* | Generated into `plugins/<module-id>/` and registered here automatically |

## Install (once)

1. Python 3.9+ and: `pip install pyyaml pdfplumber pypdf`
2. Put this folder somewhere permanent, e.g. `~/solo-rpg-workshop`. Git is recommended,
   since the modules you build are valuable.
3. In Claude Code:
   ```
   /plugin marketplace add ~/solo-rpg-workshop
   /plugin install solo-rpg-core@solo-rpg-workshop
   /plugin install solo-rpg-forge@solo-rpg-workshop
   ```
   A local-directory marketplace loads **in place**, so newly built modules and your edits
   show up after `/reload-plugins`. Nothing is copied into a cache.
4. Check: `rpg-roll 2d6` inside Claude Code (or run `plugins/solo-rpg-core/bin/rpg-roll 2d6`
   in a terminal).

On Windows, the `bin/` wrappers are bash scripts, which Claude Code runs via Git Bash. If
`python3` resolves to the Microsoft Store stub, set `SOLO_RPG_PYTHON` to your real
interpreter path.

## Workflow

```
Build a module (per book):        Per campaign vault:
  /solo-rpg-forge:ingest book.pdf   cd <vault> && claude
  (approve SURVEY.md)               /solo-rpg-forge:vault-setup "<name>" <module ids>
  /solo-rpg-forge:build-module id   /solo-rpg-forge:session-kit
  proof-read VERIFY.md              /session-start … /scene … /ask … /session-end
  /plugin install id@solo-rpg-workshop
```

- Run **ingest and build-module from the workshop folder**. Big books are resumable:
  `BUILD-STATE.md` in `staging/<id>/` tracks progress across sessions.
- Modules install **disabled**. Each vault enables only its own modules in
  `.claude/settings.json`, so rules never leak between campaigns.
- Build solo engines and oracles as their own modules (`kind: solo-engine`), so the same one
  can be combined with any game.

## Trust model

- Every roll and table result is appended to `<vault>/.solo-rpg/audit.jsonl` by the scripts.
  Vault settings deny Claude edits to that folder and to `.obsidian/`.
- Tables are data. `rpg-table validate` proves there are no gaps or overlaps.
  `rpg-table verify-report` gives you a proof-reading checklist against the book, and
  `rpg-table mark-verified` records your sign-off.
- The rules lawyer cites printed pages, or says the loaded rules don't cover the question.
- Oracle interpretation happens only through `/solo-rpg-core:interpret`, when you ask.

## Copyright

Modules contain condensed and partly verbatim text from books you own. Keep this repository
**private** and don't publish modules built from commercial books.

## Layout

```
.claude-plugin/marketplace.json
plugins/solo-rpg-core/     bin/ scripts/ skills/ agents/ references/
plugins/solo-rpg-forge/    scripts/ skills/ agents/ references/module-spec.md
plugins/<module-id>/       (generated; see module-spec.md)
staging/<module-id>/       (extraction output + SURVEY.md + BUILD-STATE.md; gitignored)
```
