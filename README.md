# solo-rpg-workshop

A Claude Code plugin marketplace for solo tabletop RPG play in Obsidian, where Claude acts
strictly as **record-keeper, dice box, table reader and rules lawyer**. Claude is never the GM.

| Plugin | What it is |
|---|---|
| `solo-rpg-core` | `rpg-roll` and `rpg-table` (on PATH while enabled), skills `roll`, `table`, `record`, `rules`, `interpret`, the `rules-lawyer` agent, and the play contract |
| `solo-rpg-forge` | The builder: `ingest` → `build-module` turn a rulebook PDF into a ruleset **module**; `vault-setup` and `session-kit` build the campaign around it |

You install these two plugins once. Everything the forge then builds — modules, agents,
session commands, templates — is written **into your own vault as project skills**, so there
is nothing to install, enable or publish per game.

## Install (once)

1. Python 3.9+ and: `pip install pyyaml pdfplumber pypdf`
2. In Claude Code:
   ```
   /plugin marketplace add gjstockham/solo-rpg-workshop
   /plugin install solo-rpg-core@solo-rpg-workshop
   /plugin install solo-rpg-forge@solo-rpg-workshop
   ```
   Install at **user** scope so they're available in every vault.
3. Check: `rpg-roll 2d6` inside Claude Code.

On Windows, the `bin/` wrappers are bash scripts, which Claude Code runs via Git Bash. If
`python3` resolves to the Microsoft Store stub, set `SOLO_RPG_PYTHON` to your real
interpreter path.

## Workflow

Everything happens in your vault. Put your PDFs in `pdfs/`, start Claude Code there, and run:

```
cd ~/Obsidian/TheOneRing && claude

/solo-rpg-forge:ingest pdfs/the-one-ring.pdf     # extract + survey, then approve SURVEY.md
/solo-rpg-forge:build-module the-one-ring        # build the module skill
/solo-rpg-forge:ingest pdfs/strider.pdf          # again for the solo engine
/solo-rpg-forge:build-module strider

/solo-rpg-forge:vault-setup "Eriador" the-one-ring strider
/solo-rpg-forge:session-kit

/session-start … /scene … /ask … /session-end    # play
```

### What ends up in the vault

```
TheOneRing/
  pdfs/                                  your books
  .claude/
    skills/
      the-one-ring/                      the module
        SKILL.md                         rules knowledge, auto-consulted
        module.yaml                      manifest: dice, records, trackers, procedures
        reference/
          rules/INDEX.md, 03-combat.md … condensed, every paragraph cited [p.N]
          tables/<group>/*.yaml          validated table data
          procedures/*.md                step-by-step, tagged and cited
          VERIFY.md                      your proof-reading checklist
      the-one-ring-journey/              one runner skill per player-facing procedure
      strider/  strider-ask-oracle/
      session-start/  scene/  ask/  session-end/  recap/  status/
    agents/rules-lawyer.md               knows this campaign's modules
    settings.json
  .solo-rpg/
    staging/<module-id>/                 extraction, SURVEY.md, BUILD-STATE.md
    audit.jsonl                          every roll and table result
  solo-rpg.yaml                          campaign config
  CLAUDE.md                              the play contract
  Sessions/  Characters/  Campaign.md  House Rules.md  Dashboards/
```

Modules are project skills, so `/reload-plugins` (or restarting Claude Code) picks up newly
built ones. There is no `/plugin install` step for a module, and no marketplace to maintain.

### Notes

- **Big books are resumable.** `BUILD-STATE.md` tracks progress, so re-running
  `/solo-rpg-forge:build-module <id>` in a later session continues where it stopped.
- **One vault per campaign.** Each vault holds only its own modules, so rules never leak
  between campaigns. To use a solo engine in a second campaign, ingest its PDF there too.
- **Build solo engines and oracles as their own modules** (`kind: solo-engine`), so a game
  module stays independent of how you generate scenes.
- **The vault is the project.** Claude Code must be started from the vault root.

## Trust model

- Every roll and table result is appended to `<vault>/.solo-rpg/audit.jsonl` by the scripts.
  Vault settings deny Claude edits to that file and to `.obsidian/`.
- Tables are data. `rpg-table validate` proves there are no gaps or overlaps.
  `rpg-table verify-report` gives you a proof-reading checklist against the book, and
  `rpg-table mark-verified` records your sign-off.
- The rules lawyer cites printed pages, or says the loaded rules don't cover the question.
- Oracle interpretation happens only through `/solo-rpg-core:interpret`, when you ask.

## Copyright

Modules contain condensed and partly verbatim text from books you own. They live in your
vault, so keep that vault **private** and don't publish modules built from commercial books.
This repo ships only the tools and contains no book content.

## Developing this repo

```
.claude-plugin/marketplace.json
plugins/solo-rpg-core/     bin/ scripts/ skills/ agents/ references/
plugins/solo-rpg-forge/    scripts/ skills/ agents/ references/module-spec.md
```

`references/module-spec.md` defines every file a module contains. To test local changes, add
this checkout as a marketplace (`/plugin marketplace add <path>`) and run the forge from a
scratch vault elsewhere — the scripts refuse to build inside this repo.
