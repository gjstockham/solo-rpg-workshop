# Design: solo-rpg-gm — Claude runs a published adventure

Status: **draft for review**. Nothing here is built yet.

A third plugin in this marketplace, `solo-rpg-gm`, lets Claude act as **game master for a
published adventure module**. The player runs the party. Claude reads the adventure,
describes what the characters perceive, runs the monsters and NPCs, adjudicates with the
rules module, and keeps the world's hidden state.

This is a separate play style from `solo-rpg-core` + `solo-rpg-forge`, where the player is
the GM and Claude is a clerk. The two do not mix in one campaign. A vault is one style or
the other, and its `CLAUDE.md` says which.

The plugin knows nothing about any particular game. Everything system-specific comes from
the rules module (built by the forge from the rulebook) and the adventure module (built by
this plugin from the adventure PDF). Both are made the same way: extract the PDF, survey
it, and generate whatever the book turns out to need.

## Contents
1. Goals, non-goals and priorities
2. How it fits the existing plugins
3. The GM contract
4. Secrets: what the player sees and what they don't
5. Adventure modules
6. Building an adventure
7. Campaign vault
8. Hidden state
9. Playing
10. Improvisation and the oracle
11. Party and balance
12. Changes to solo-rpg-core and solo-rpg-forge
13. Milestones
14. Decisions and open questions

## 1. Goals, non-goals and priorities

**Goals (v1)**
- Run a published adventure **as written**. Its places, people, events and treasure are the
  facts of the world. Claude improvises only where the adventure is silent (section 10).
- Work for any system the forge can build a rules module for. No game-specific code,
  skills or structure in the plugin.
- Keep the trust model of the existing tools. All dice come from scripts, every roll is
  logged, and rulings cite the rules module.
- Keep state across sessions and across several adventures in one campaign.
- Keep the player unspoiled during normal play, as far as that doesn't slow play down
  (section 4).

**Priority.** When secrecy and a smooth game conflict, **the smooth game wins**. Spoiler
protection is a set of cheap habits, not a gate the game has to pass through.

**Non-goals (v1)**
- Generating adventures. The adventure is the book's, not Claude's.
- Maps as maps. Play is theatre of the mind. Connections between places come from the
  adventure's text and maps where they can be read, but there is no map rendering or grid.
- GM personality or voice. v1 uses one default narration style (section 9.4).
- Rebalancing modes beyond the adventure's own guidance (section 11 lists what comes later).
- Mixing with the clerk-style solo engines in the same campaign.

## 2. How it fits the existing plugins

| Plugin | Role in a GM campaign |
|---|---|
| `solo-rpg-core` | `rpg-roll`, `rpg-table` and the audit trail. Gains secret rolls and a sealed log (section 12) |
| `solo-rpg-forge` | Builds the **rules module** (`kind: game`) from the rulebook exactly as today, with its normal ingest and survey deciding the scope. Its `pdf_extract.py` and `table-transcriber` agent are reused to build adventures |
| `solo-rpg-gm` (new) | Builds **adventure modules**, sets up a GM vault, and runs play |

`solo-rpg-gm` declares `dependencies: [solo-rpg-core, solo-rpg-forge]` in its
`plugin.json`, and finds the forge's scripts the same way the forge finds core
(`vaultpaths.find_core()`), as a sibling in the same marketplace.

Plugin layout:

```
plugins/solo-rpg-gm/
  .claude-plugin/plugin.json
  bin/rpg-gm                         state, checks and reveal (section 8)
  scripts/gm_tool.py  adventure_tool.py
  skills/
    ingest-adventure/                PDF → staging + survey (section 6)
    build-adventure/                 survey → adventure module (section 6)
    gm-vault-setup/                  campaign vault and GM contract (section 7)
    start/  end/  recap/  status/  challenge/  reveal/  adventure/   play (section 9)
  agents/
    element-writer.md                transcribes one batch of adventure elements
    adventure-auditor.md             checks the built adventure against the book
    keeper.md                        runtime reader of the adventure (section 4.3)
  references/
    gm-contract.md                   copied into the vault CLAUDE.md
    adventure-spec.md                every file an adventure module can contain
    oracle/                          a small original yes/no oracle (section 10)
```

All commands keep the plugin prefix (`/solo-rpg-gm:start`), consistent with
`/solo-rpg-forge:*` and `/solo-rpg-core:*`.

## 3. The GM contract

`references/gm-contract.md` replaces the clerk contract in a GM vault's `CLAUDE.md`. Draft:

> **The player runs the party. Claude runs everything else, from the adventure as written.**
>
> **What Claude does**
> - **Runs the adventure.** The adventure module is the source of truth for places, people,
>   monsters, treasure and events. Read-aloud text is given exactly as printed.
> - **Describes only what the characters perceive.** It doesn't state a hidden fact, a
>   monster's remaining hit points, a target number, a trap or a secret until the
>   characters discover it.
> - **Adjudicates with the rules module**, citing `[p.N]` when asked or when a ruling is
>   unusual. Ambiguous rules get a ruling now, recorded in `House Rules.md`, and the
>   player may `/solo-rpg-gm:challenge` it.
> - **Rolls every die with the scripts.** GM rolls are open unless the characters wouldn't
>   know about them (section 9.2).
> - **Keeps the world's state** with `rpg-gm`, and records every improvised fact as canon.
> - **Keeps the game moving.** A quick, reasonable ruling now beats a perfect one later.
>
> **What Claude does not do**
> - **No dice from its own head.** If a script fails, report the error and stop.
> - **No changing the adventure** to be easier, harder or more interesting. The dice fall
>   where they fall, including character death.
> - **No big invented facts.** Anything that would change the adventure's course, a named
>   NPC's nature or the party's fate is put to the oracle, not decided (section 10).
> - **No acting for the characters.** Claude never decides what a PC does, says or feels.
>   When the rules need a player choice, it stops and asks.
> - **No spoilers**, in or out of character. Out-of-character questions ("OOC: …") get
>   rules answers, not adventure answers.
>
> **Style**: see section 9.4.

The clerk contract's "no invented fiction" is intentionally replaced by "no fiction beyond
the adventure, except minor, consistent detail, recorded as canon".

## 4. Secrets: what the player sees and what they don't

Claude must read the adventure, and the player would rather not. Section 1's priority
applies throughout: these are habits that cost nothing during play, and none of them may
make play slower or clumsier.

### 4.1 What we can and can't promise

**"Nothing spoils you during normal play"**, not a security boundary. The player owns the
machine and can always open any file or expand any tool call.

| Surface | Habit |
|---|---|
| Obsidian | All GM material lives under `.solo-rpg/`. Obsidian doesn't show dot-folders |
| Claude's replies | The contract forbids hidden facts. `/solo-rpg-gm:status` reads only player-known notes |
| Tool calls shown in Claude Code | Shown collapsed, but the **command line and file path are visible**. So ids are neutral (`loc-05`, `npc-03`, `stat-02`), never descriptive, and secret-roll labels are generic (`gm check`) |
| Tool results, subagent output, Claude's thinking | Collapsed or hidden by default. The player is told not to expand them during play if they want to stay unspoiled |
| Skill listings | Adventures are **not** skills, so their descriptions never appear in the skill list (section 5.1) |
| Build checkpoints | Spoiler-free summaries (section 6) |

### 4.2 Player-known vs hidden

Two sets of records:

- **Player-known**, in the Obsidian vault: character notes, session logs, a `Known/`
  folder of places, people and clues the party has actually learned, and handouts once
  they're found.
- **Hidden**, under `.solo-rpg/`: the adventure module, the world state, canon, the
  sealed roll log.

A fact moves from hidden to player-known only when the characters learn it in play. Claude
writes the player-known note at that moment, in the party's words ("the old woman said…"),
not the adventure's.

### 4.3 The keeper agent

The main reason for the keeper is **context**: a whole adventure won't fit comfortably in
the conversation, and play should only carry what the current scene needs. Keeping
secrets out of the transcript is a side benefit.

When the party arrives somewhere new, starts a significant interaction, or does something
the scene brief doesn't cover, Claude asks the `keeper`. It reads the relevant adventure
files plus the current state and returns:

```
PERCEIVED   what the characters perceive now; read-aloud text verbatim, marked
BRIEF       the hidden elements relevant to this place or action: what a search would
            find, who is here, what's lurking, triggers, the rules and rolls involved,
            stat block ids to put in play
STATE       state changes this implies (for Claude to apply with rpg-gm)
CITES       [p.N] for each item
```

Claude keeps the brief in context for the rest of the scene rather than re-asking. When
it's quicker to open an adventure file directly (a stat block mid-fight, a single line
it needs to check), it does.

**Model.** The keeper's model is the player's choice, trading cost against quality.
`gm-vault-setup` writes a vault copy of the agent to `.claude/agents/keeper.md` (as
`vault-setup` does for the rules lawyer) with the `model:` the player picks, and the player
can change it there at any time. The default is to inherit the session's model.

## 5. Adventure modules

### 5.1 Where they live and why they aren't skills

```
<vault>/.solo-rpg/adventures/<adv-id>/
  adventure.yaml           manifest (5.2)
  overview.md              GM synopsis: background, what's going on, how it can end [p.N]
  INDEX.md                 every element: id → title → page → one line
  <element-type>/<id>.md   one file per element, for each type the survey found (5.3)
  tables/<group>/*.yaml    random tables, standard rpg-table format
  README.md  AUDIT.md      build log and audit (hidden)
```

Rules modules are skills because Claude should consult them automatically. An adventure
is the opposite: Claude should reach it deliberately, mostly through the keeper, and its
skill description would leak into the skill list. So adventures are plain data under
`.solo-rpg/`, and the play skills and keeper know where to find them.

Ids are neutral: a short type prefix and a number (`loc-05`, `npc-03`). Where the book keys
something (location "12b"), the key goes in the id (`loc-12b`). Titles live inside the
files, never in paths.

### 5.2 adventure.yaml

```yaml
id: adv-01                  # neutral; the title is below
title: "<as printed>"
requires: [<rules-module-id>]
sources: [{pdf: pdfs/<file>.pdf, offset: 2}]
party:                      # the adventure's own guidance, as printed, cited
  guidance: "<as printed>"
  source: "p.1"
scaling: []                 # the adventure's own scaling notes, if any, cited
start: {element: loc-01, note: "<how play begins, cited>"}
elements:                   # only the types this adventure has (5.3)
  locations: [loc-01, loc-02]
  npcs: [npc-01]
  stat-blocks: [stat-01]
  events: [ev-01]
  handouts: [h-01]
clocks:                     # countdowns or timelines the adventure defines
  - {id: clk-01, max: 6, source: "p.3"}
tables: [adv-01/<table-id>]
rules_topics: []            # rules the adventure calls on, as named in the rules module INDEX
```

### 5.3 Element types

The survey decides which element types an adventure needs, as the forge's survey decides a
rules module's records, trackers and procedures. The spec defines a vocabulary of common
types so similar adventures come out alike, but a book can add its own.

| Type | Typical source | Holds |
|---|---|---|
| `locations` | keyed areas, sites, rooms, regions | read-aloud, what's visible, what's hidden and how it's found, who's here, treasure, triggers, connections |
| `npcs` | named characters | wants, knows (each secret with what it takes to learn it), printed dialogue verbatim, reaction, stat block ref |
| `stat-blocks` | monster and NPC statistics | the stat line verbatim plus structured `fields` (5.4) |
| `events` | timelines, triggered scenes, reinforcements | trigger, effect, once or repeating |
| `clues` | investigation-style adventures | what it reveals, where it can be found (several places if the book says so) |
| `scenes` | scene- or chapter-based adventures | how it starts, what's at stake, how it can end, where it leads |
| `factions` | groups with goals | goals, resources, what they do if left alone |
| `handouts` | player handouts | text as given to the players, verbatim |

Each element file has frontmatter (`id`, `title`, `source`, and type-specific references
such as `connections`, `stat`, `events`) and `##` sections, each carrying `[p.N]`. Sections
that hold hidden material are named so (`## Hidden`), so the keeper knows what not to put
in PERCEIVED.

A location's `connections` list where the location leads, with `visible: false` and a
cited `find:` for hidden routes:

```yaml
connections:
  - {to: loc-04, via: "<as printed>", visible: true}
  - {to: loc-06, via: "<as printed>", visible: false, find: "<how, as printed> [p.7]"}
```

Connections come from the text first, then from the adventure's maps where the text is
silent, marked `from: map`. `rpg-gm check` confirms every connection resolves and every
location is reachable from the start. That's the whole of "maps" in v1.

### 5.4 Stat blocks

Structured, so scaling (section 11) is arithmetic. The field names come from the rules
module: if its `module.yaml` defines a stat-block record, those fields are used;
otherwise the fields are taken from the stat line as printed and listed in
`adventure.yaml` for consistency.

```yaml
id: stat-02
title: "<as printed>"
source: "p.7"
statline: "<verbatim stat line>"
fields: {hp: 9, ...}          # the rules module's stat-block fields
hp_roll: "2d8"                # if the book gives hit dice rather than fixed hp
notes: "tactics, morale, special abilities, verbatim where mechanical"
```

### 5.5 Page citations

Same rule as rules modules: every section and bullet carries `[p.N]` (printed page), so
the GM, the auditor and `/solo-rpg-gm:challenge` can check against the book.

## 6. Building an adventure

Two stages, mirroring the forge's `ingest` → `build-module`, and resumable the same way
via `BUILD-STATE.md`. Staging goes in `.solo-rpg/staging/<adv-id>/`.

**`/solo-rpg-gm:ingest-adventure <pdf> [adv-id]`**
1. **Preconditions.** The rules module the adventure is for already exists in the vault.
   If not, send the player to `/solo-rpg-forge:ingest` for the rulebook first.
2. **Extract** with the forge's `pdf_extract.py`, exactly as `ingest` does.
3. **Page numbering**, as `ingest` does.
4. **Survey** into `SURVEY.md`, which **the player doesn't read**. As well as the usual
   chapter table, it records: the adventure's structure (site-based, event-driven,
   investigation, scene-based, or a mix), the element types it needs and a count of each,
   tables, handouts, clocks, stat blocks and their format, rules topics the adventure
   calls on (checked against the rules module's INDEX), and extraction risks.
5. **Spoiler-free checkpoint.** The player is shown: title, page count, page offset, the
   party guidance, the adventure's structure, counts per element type, rules topics the
   rules module doesn't cover, and extraction risks by page number. They approve or adjust
   the scope.

**`/solo-rpg-gm:build-adventure <adv-id>`**
1. Scaffold the adventure folder and `adventure.yaml` from the survey.
2. **Elements** (parallel): `element-writer` agents, one batch of elements each, writing
   element files and returning the references they found (stat blocks, events, tables).
   The overview, `INDEX.md` and anything cross-cutting (clocks, factions) are written by
   the main session, which has the whole picture.
3. **Tables** with the forge's `table-transcriber` agent, into the adventure's `tables/`.
4. **Check.** `rpg-gm check <adv-id>`: ids and references resolve, every location is
   reachable, every section is cited, `rpg-table validate` passes on its tables.
5. **Audit.** `adventure-auditor` spot-checks elements, stat blocks and tables against the
   pages (like `module-auditor`) and writes `AUDIT.md`. Claude fixes confirmed defects.
6. **Hand-off.** The player sees counts only: checks passed, defects found and fixed,
   anything unresolved by page number. `AUDIT.md` can be read after the adventure with
   `/solo-rpg-gm:reveal`.

Proof-reading by the player isn't possible without spoilers, so the auditor carries that
job. Stat blocks and tables are checked as strictly as a rules module's.

If the rules module lacks topics the adventure needs, the player can extend it with the
forge (resuming `build-module` with an updated survey) before or during the adventure.

## 7. Campaign vault

`/solo-rpg-gm:gm-vault-setup "<campaign>" <rules-module-ids>`, run in the vault root.
Like `vault-setup`, it proposes before writing and adapts to an existing vault. It reuses
the rules module's manifest to design the character notes (records, trackers) the same
way `vault-setup` does.

```
<vault>/
  pdfs/
  .claude/
    skills/<rules-module>/ …              rules module (from the forge)
    skills/gm-oracle/                     small oracle module (section 10)
    agents/rules-lawyer.md                campaign copy, as today
    agents/keeper.md                      campaign copy, with the player's model choice
    settings.json
  .solo-rpg/
    adventures/<adv-id>/                  adventure modules (hidden)
    gm/<adv-id>/state.yaml, canon.md, state-log.jsonl
    audit.jsonl  sealed.jsonl
    staging/
  solo-rpg.yaml
  CLAUDE.md                               GM contract + vault map
  Characters/  Sessions/  Known/  Handouts/  Campaign.md  House Rules.md
```

`solo-rpg.yaml` gains:

```yaml
style: gm                     # vs the default clerk style
modules: [<rules-module>, gm-oracle]
adventures:
  - {id: adv-01, status: active}       # planned | active | finished | abandoned
active_adventure: adv-01
party_mode: as-written        # section 11
session_log: terse            # v1 has only terse; other styles later
current_session: Sessions/Session 01.md
```

`settings.json` also allows `rpg-gm` and denies Claude edits to `sealed.jsonl` and to
`.solo-rpg/gm/**/state-log.jsonl`. `state.yaml` is changed through `rpg-gm`, so every
change is logged.

Several adventures per campaign: characters, `Known/` and sessions carry across. Each
adventure has its own module and its own `gm/<adv-id>/` state. `/solo-rpg-gm:adventure`
switches the active one, lists them, or marks one finished.

## 8. Hidden state

`.solo-rpg/gm/<adv-id>/state.yaml`:

```yaml
current: loc-05               # where the party is (or the current scene)
time: {elapsed: 14, unit: "<the adventure's or rules module's unit>"}
elements: {loc-01: explored, loc-05: entered, npc-01: {status: alive, attitude: wary, met: true}}
instances:                    # stat blocks put in play
  stat-02#1: {at: loc-05, hp: 5, status: active}
  stat-02#2: {at: loc-05, hp: 0, status: dead}
flags:  {ev-02: fired}
clocks: {clk-01: 2}
taken:  [loc-03/treasure-1]
```

`canon.md` records every improvised fact (section 10), with session and scene, so
improvisation stays consistent across sessions.

`rpg-gm` (in the new plugin):

| Command | Does |
|---|---|
| `rpg-gm state show [path]` | Print state (for Claude; never shown to the player as such) |
| `rpg-gm state set <path> <value> --why "<ref>"` | Change a value; logs old → new to `state-log.jsonl` |
| `rpg-gm spawn <stat-id> [--count N] [--at loc-05]` | Create instances; hp from `fields.hp`, or rolled from `hp_roll` with `rpg-roll --secret` |
| `rpg-gm damage <instance> <n>` / `tick <clock> [n]` | Common shortcuts, logged |
| `rpg-gm canon "<fact>" --basis "<why>"` | Append to `canon.md` |
| `rpg-gm check <adv-id>` | Validate an adventure module (section 6) |
| `rpg-gm reveal [adv-id]` | Print the sealed log and verify it against the audit hashes (section 12) |

Output uses neutral ids.

## 9. Playing

### 9.1 Commands (v1)

| Command | Does |
|---|---|
| `/solo-rpg-gm:start` | New session note; short recap from player-known notes; resume where the party is (the keeper reads it) |
| (plain messages) | The player's actions. This is the whole game loop (9.2) |
| `/solo-rpg-gm:status` | Party sheets, what the party knows, open leads. Player-known only |
| `/solo-rpg-gm:recap [n]` | Recap of the last n sessions from the session notes |
| `/solo-rpg-gm:challenge` | The rules lawyer reviews the last ruling against the rules module and house rules. If it disagrees with a citation, the GM corrects the ruling. If the rules are ambiguous, the player decides and it's recorded in `House Rules.md` |
| `/solo-rpg-gm:end` | Close the session: player-known notes updated, state saved, loose ends (as the party knows them) listed |
| `/solo-rpg-gm:adventure` | List, start, switch or finish adventures |
| `/solo-rpg-gm:reveal` | After an adventure is finished: sealed rolls, what was missed, `AUDIT.md`. Asks for confirmation first |

Character creation uses the rules module's own procedure runners, built by the forge, so
it isn't duplicated here.

### 9.2 The loop

For each player message:

1. **Understand the action.** If it's unclear what the characters are doing, ask. Never
   fill in a PC's action.
2. **Consult.** Use the scene brief already in context, or ask the keeper when the party
   moves on or does something the brief doesn't cover.
3. **Resolve.** Apply the rules module. Player rolls are asked for and made with
   `rpg-roll` or physical dice. **GM rolls are open by default**, including monster
   attacks and damage. A GM roll is `--secret` only when the characters wouldn't know it
   happened or what it means: a surprise attack, a hidden creature's check, a check
   against the party that they wouldn't notice, an oracle roll.
4. **Improvise if needed** (section 10).
5. **Narrate** the outcome (9.4).
6. **Record.** `rpg-gm` for hidden state; character notes for the rules module's
   player-facing records (written openly); `Known/` for what the party learned; one line
   per event in the session note (9.5).

Out-of-character questions start with "OOC:". The GM answers rules questions, can remind
the player of anything the party knows, and declines anything else.

### 9.3 Combat

Initiative, actions and results come from the rules module. Instances come from
`rpg-gm spawn`. Hidden hp is tracked in state and not stated; descriptions show condition
in the fiction ("it staggers"). Morale follows the adventure, then the rules module. PC
death follows the rules module.

### 9.4 Default narration style

- Second person plural, present tense ("You see…").
- Read-aloud text verbatim, as a blockquote, before anything else.
- Otherwise 2–5 sentences: what changed, what's now apparent, what's pressing. No purple
  prose, no inner thoughts for the PCs, no hints about hidden things.
- Mechanics after the fiction, in one line: the roll and its result, and state changes the
  party would know about.
- End on the situation, not on a menu of options. Ask "what do you do?" only when it's
  unclear whose turn it is.

Personality and voice come later.

### 9.5 Session log (terse)

The session note gets one line per event, no prose: scene changes, open rolls (as
`rpg-roll --log` writes them), "GM rolled (hidden)" for secret rolls, discoveries, damage,
deaths, loot, and rulings. A heading per scene. Other log styles are for later.

## 10. Improvisation and the oracle

Every question the adventure doesn't answer is resolved by this ladder, in order:

1. **The adventure says.** Use it, cited.
2. **The rules module says** (reactions, morale, random encounters, searching, whatever it
   provides). Use it.
3. **Minor detail consistent with what's established** (the colour of a door, the smell
   of a room, an unnamed guard's line of dialogue). Claude decides and moves on. If it
   might matter again, record it with `rpg-gm canon`.
4. **Anything significant.** A new fact about a named NPC or place, anything that could
   change the adventure's path, or anything that would help or hurt the party noticeably.
   Claude frames a yes/no question, picks a likelihood from what's established, rolls the
   oracle with `rpg-table roll gm-oracle/yes-no --secret`, follows the answer, and records
   the result with `rpg-gm canon`.

Claude never pre-decides the answer to a step-4 question and then rolls for show. The
likelihood is chosen, and stated in the canon entry, before the roll.

**The oracle.** `gm-vault-setup` writes a tiny module `gm-oracle` into the vault: one
original yes/no table by likelihood (with "yes, and" / "no, but" results) and one original
table for an NPC's attitude. Both are ours, not copied from any published solo engine.
The player can swap in a solo-engine module of their own later.

## 11. Party and balance

`party_mode` in `solo-rpg.yaml`:

| Mode | v1? | Meaning |
|---|---|---|
| `as-written` | yes | Use the adventure's party guidance. The player controls the whole party |
| `scaled` | later | Apply the adventure's own scaling notes (`adventure.yaml → scaling`), or the rules module's, to instance counts and hp at spawn time |
| `dm-yourself` | later | One PC plus a sidekick, 2 levels above the adventure's level, max hp; instance hp and counts × ¾. Applied by `rpg-gm spawn` |

Scaling always happens at spawn time and is recorded on the instance (`scaled: 0.75`),
never by editing the adventure module. `dm-yourself` assumes a level-based system; where
the rules module has no levels, the mode is unavailable.

## 12. Changes to solo-rpg-core and solo-rpg-forge

Small, and compatible with the clerk style:

1. **`rpg-roll --secret` and `rpg-table roll --secret`.** The full result is appended to
   `.solo-rpg/sealed.jsonl` and printed to stdout (the GM needs it). `audit.jsonl` gets a
   stub `{type, secret: true, label, sha256}` with the hash of the sealed record, so the
   sealed log can be checked for tampering at `/solo-rpg-gm:reveal`. `--log` writes "GM
   rolled (hidden) — <label>" to the session note.
2. **Adventure tables.** `common.module_dirs()` also finds
   `.solo-rpg/adventures/*/tables` when called with `--gm` (or `SOLO_RPG_GM=1`).
   `rpg-table list` without `--gm` doesn't show adventure tables.
3. **Forge.** No behaviour change. The GM plugin calls its `pdf_extract.py` and dispatches
   its `table-transcriber` agent. `module_tool.py` doesn't gain an `adventure` kind;
   adventures have their own spec and tool.
4. **README.** The marketplace intro stops saying "Claude is never the GM" globally, and
   instead describes the two styles and which plugins each uses.

## 13. Milestones

| # | Deliverable | Done when |
|---|---|---|
| M0 | This design | Reviewed and agreed |
| M1 | Core changes (section 12.1–12.2) | Secret rolls, sealed log, hash check and hidden adventure tables all work from the CLI |
| M2 | Adventure spec, `rpg-gm check`, `ingest-adventure`, `build-adventure`, `element-writer`, `adventure-auditor` | A small published adventure builds, checks clean and audits, with only spoiler-free output shown |
| M3 | `gm-vault-setup`, GM contract, `gm-oracle` module | A fresh vault with a forge-built rules module is set up for GM play |
| M4 | `keeper`, `rpg-gm` state commands, play skills | A full session can be played, ended and resumed |
| M5 | Playtest end to end | Notes on what broke, fed back into the spec |
| Later | `scaled` and `dm-yourself` modes, GM personality, other log styles, better map handling | — |

## 14. Decisions and open questions

**Decided**
- One repo, a third plugin, `solo-rpg-gm`. All commands keep the `solo-rpg-*:` prefix.
- System-agnostic. The rules module comes from the forge's normal ingest, and the
  adventure's structure comes from its own survey.
- Improvisation follows the ladder in section 10, with an original oracle for significant
  questions.
- `as-written` party mode first; the player controls the party.
- Theatre of the mind, with connections taken from the adventure's text and maps.
- One vault per campaign, several adventures per campaign, no mixing with the clerk style.
- Read-aloud text verbatim; one default narration style.
- GM rolls open unless the characters wouldn't know about them.
- Terse session log.
- Keeper model is the player's choice. Smooth play takes priority over secrecy.

**Open**
1. **Test adventure.** A small published adventure, and a rulebook the forge can build a
   rules module from, to exercise M2–M5. Something site-based is the simplest first case.
2. **Element vocabulary.** Section 5.3's types are a starting guess. The first two or three
   adventures built will show whether they hold up or need changing.
