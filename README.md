# solo-rpg-workshop

A Claude Code plugin marketplace for solo tabletop RPG play in Obsidian. In the main play
style (`solo-rpg-core` + `solo-rpg-forge`), Claude acts strictly as **record-keeper, dice
box, table reader and rules lawyer**, and is never the GM. A second style, where Claude runs
a published adventure as GM (`solo-rpg-gm`), is newer and not yet playtested; see
[GM style](#gm-style-claude-runs-a-published-adventure). A campaign uses one style or the
other.

| Plugin | What it is |
|---|---|
| `solo-rpg-core` | `rpg-roll`, `rpg-table` and `rpg-sealed` (on PATH while enabled), skills `roll`, `table`, `record`, `rules`, `interpret`, the `rules-lawyer` agent, and the play contract |
| `solo-rpg-forge` | The builder: `ingest` → `build-module` turn a rulebook PDF into a ruleset **module**; `vault-setup` and `session-kit` build the campaign around it |
| `solo-rpg-gm` | **New, not yet playtested.** A separate play style where Claude *is* the GM: `ingest-adventure` → `build-adventure` turn an adventure PDF into a hidden adventure module; `gm-vault-setup` sets up the vault; `start` … `end` run sessions. `rpg-gm` on PATH. Needs the other two |

You install the plugins once. Everything the forge then builds — modules, agents,
session commands, templates — is written **into your own vault as project skills**, so there
is nothing to install, enable or publish per game.

## Install (once)

1. Python 3.9+ and: `pip install pyyaml pdfplumber pypdf`
2. In Claude Code:
   ```
   /plugin marketplace add gjstockham/solo-rpg-workshop
   /plugin install solo-rpg-core@solo-rpg-workshop
   /plugin install solo-rpg-forge@solo-rpg-workshop
   /plugin install solo-rpg-gm@solo-rpg-workshop       # only for the GM style
   ```
   Install at **user** scope so they're available in every vault.
3. Check: `rpg-roll 2d6` inside Claude Code.

On Windows, the `bin/` wrappers are bash scripts, which Claude Code runs via Git Bash. If
`python3` resolves to the Microsoft Store stub, set `SOLO_RPG_PYTHON` to your real
interpreter path.

## Clerk style: you are the GM

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

Modules are project skills, so there is no `/plugin install` step for a module and no
marketplace to maintain. Claude Code watches `.claude/skills/` and picks up new modules
during a session. Restart it only after the **first** module in a vault (the directory has to
exist at launch to be watched) and after `vault-setup` writes `.claude/agents/rules-lawyer.md`.

### Notes

- **Big books are resumable.** `BUILD-STATE.md` tracks progress, so re-running
  `/solo-rpg-forge:build-module <id>` in a later session continues where it stopped.
- **One vault per campaign.** Each vault holds only its own modules, so rules never leak
  between campaigns. To use a solo engine in a second campaign, ingest its PDF there too.
- **Build solo engines and oracles as their own modules** (`kind: solo-engine`), so a game
  module stays independent of how you generate scenes.
- **The vault is the project.** Claude Code must be started from the vault root.

## GM style: Claude runs a published adventure

The player runs the party. Claude reads the adventure, describes what the characters
perceive, runs everyone else, and adjudicates with the rules module, following the adventure
as written and asking a built-in oracle when it has to improvise something significant.
The design, and why it works as it does, is in [`docs/gm-design.md`](docs/gm-design.md).

It uses its **own vault**: one campaign, one style. The rules still come from a module the
forge builds from your rulebook.

```
cd ~/Obsidian/MyCampaign && claude

/solo-rpg-forge:ingest pdfs/core-rules.pdf           # the rulebook, as in the clerk style
/solo-rpg-forge:build-module my-game

/solo-rpg-gm:ingest-adventure pdfs/adventure.pdf     # spoiler-free summary to approve
/solo-rpg-gm:build-adventure adv-01                  # builds, checks and audits it, hidden

/solo-rpg-gm:gm-vault-setup "My Campaign" my-game    # contract, oracle, notes; then restart
/my-game-character-creation                          # whatever the rules module provides

/solo-rpg-gm:start                                   # then just say what the party does
/solo-rpg-gm:end
```

Also: `/solo-rpg-gm:status` and `recap` (from your own notes), `challenge` (dispute a
ruling), `adventure` (list, switch, finish), and `reveal` (after an adventure, everything
that was hidden). "OOC:" marks an out-of-character question.

**Keeping it unspoiled.** Everything the player shouldn't see lives under `.solo-rpg/`,
which Obsidian doesn't show: the adventure module, the world state, improvised canon and
the sealed log of secret rolls. Build steps and tool output refer to adventure content by
neutral ids (`loc-05`, `npc-03`). Claude Code still shows collapsed tool output and Claude's
thinking, so this is "nothing spoils you in normal play", not a lock. A smooth game comes
first.

What a GM vault adds:

```
MyCampaign/
  .claude/
    skills/my-game/  gm-oracle/          rules module; the built-in yes/no and attitude oracle
    agents/rules-lawyer.md  keeper.md    the keeper reads the adventure for the GM (you pick its model)
  .solo-rpg/                             hidden from the player
    adventures/adv-01/                   the adventure module: locations, NPCs, stat blocks, events …
    gm/adv-01/                           state.yaml, state-log.jsonl, canon.md
    audit.jsonl  sealed.jsonl
  solo-rpg.yaml                          style: gm, adventures, party mode
  CLAUDE.md                              the GM play contract
  Characters/  Sessions/  Known/  Handouts/  Campaign.md  House Rules.md  Dashboards/
```

`Known/` holds what the party has actually learned, in their words. Several adventures can
share one campaign; the characters carry over.

## Trust model

- Every roll and table result is appended to `<vault>/.solo-rpg/audit.jsonl` by the scripts.
  Vault settings deny Claude edits to that file and to `.obsidian/`.
- Secret rolls (`--secret`, GM style only) go to `.solo-rpg/sealed.jsonl`, with only their
  hash in the audit trail. `rpg-sealed verify` checks the two match without showing any
  result; `/solo-rpg-gm:reveal` shows them after the adventure. Hidden world state changes
  only through `rpg-gm`, which logs every change.
- Tables are data. `rpg-table validate` proves there are no gaps or overlaps.
  `rpg-table verify-report` gives you a proof-reading checklist against the book, and
  `rpg-table mark-verified` records your sign-off.
- The rules lawyer cites printed pages, or says the loaded rules don't cover the question.
- Oracle interpretation happens only through `/solo-rpg-core:interpret`, when you ask.

## Copyright

Modules and adventure modules contain condensed and partly verbatim text from books you own. They live in your
vault, so keep that vault **private** and don't publish modules built from commercial books.
This repo ships only the tools and contains no book content.

## Developing this repo

```
.claude-plugin/marketplace.json
plugins/solo-rpg-core/     bin/ scripts/ skills/ agents/ references/
plugins/solo-rpg-forge/    scripts/ skills/ agents/ references/module-spec.md
plugins/solo-rpg-gm/       bin/ scripts/ skills/ agents/ references/adventure-spec.md
docs/gm-design.md
```

`references/module-spec.md` defines every file a module contains, and
`plugins/solo-rpg-gm/references/adventure-spec.md` every file an adventure module contains.
`docs/gm-design.md` is the design for the GM style, with its milestones. To test local changes, add
this checkout as a marketplace (`/plugin marketplace add <path>`) and run the forge from a
scratch vault elsewhere — the scripts refuse to build inside this repo.
