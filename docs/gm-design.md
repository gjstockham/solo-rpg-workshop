# Design: solo-rpg-gm — Claude runs a published adventure

Status: **draft for review**. Nothing here is built yet.

A third plugin in this marketplace, `solo-rpg-gm`, lets Claude act as **game master for a
published adventure module**. The player runs the party. Claude reads the adventure,
describes what the characters perceive, runs the monsters and NPCs, adjudicates with the
rules module, and keeps the world's hidden state.

This is a separate play style from `solo-rpg-core` + `solo-rpg-forge`, where the player is
the GM and Claude is a clerk. The two do not mix in one campaign. A vault is one style or
the other, and its `CLAUDE.md` says which.

First target: a small **Dungeon Crawl Classics** adventure (ideally a 0-level funnel), run
with the rules from a `dcc` rules module built by the existing forge.

## Contents
1. Goals and non-goals
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
14. Open questions

## 1. Goals and non-goals

**Goals (v1)**
- Run a published adventure **as written**. Its areas, NPCs, events and treasure are the
  facts of the world. Claude improvises only where the adventure is silent (section 10).
- Keep the player unspoiled during normal play (section 4).
- Keep the trust model of the existing tools. All dice come from scripts, every roll is
  logged, and rulings cite the rules module.
- Keep state across sessions and across several adventures in one campaign.
- DCC first, but nothing DCC-specific in the plugin itself. System specifics come from the
  rules module and the adventure module.

**Non-goals (v1)**
- Generating adventures. The adventure is the book's, not Claude's.
- Maps as maps. Play is theatre of the mind. Area connections come from the adventure's key
  and maps where they can be read, but there is no map rendering or grid (section 5.3).
- GM personality or voice. v1 uses one default narration style (section 9.4).
- Rebalancing modes beyond the adventure's own guidance (section 11 lists what comes later).
- Mixing with the clerk-style solo engines in the same campaign.

## 2. How it fits the existing plugins

| Plugin | Role in a GM campaign |
|---|---|
| `solo-rpg-core` | `rpg-roll`, `rpg-table` and the audit trail. Gains secret rolls and a sealed log (section 12) |
| `solo-rpg-forge` | Builds the **rules module** (`kind: game`, e.g. `dcc`) exactly as today. Its `pdf_extract.py` and `table-transcriber` agent are reused to build adventures |
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
    build-adventure/                 PDF → adventure module (section 6)
    gm-vault-setup/                  campaign vault and GM contract (section 7)
    start/  end/  recap/  status/  challenge/  reveal/  adventure/   play (section 9)
  agents/
    area-writer.md                   transcribes keyed areas
    adventure-auditor.md             checks the built adventure against the book
    keeper.md                        runtime reader of the adventure (section 4.3)
  references/
    gm-contract.md                   copied into the vault CLAUDE.md
    adventure-spec.md                every file an adventure module contains
    oracle/                          a small original yes/no oracle (section 10)
```

## 3. The GM contract

`references/gm-contract.md` replaces the clerk contract in a GM vault's `CLAUDE.md`. Draft:

> **The player runs the party. Claude runs everything else, from the adventure as written.**
>
> **What Claude does**
> - **Runs the adventure.** The adventure module is the source of truth for places, people,
>   monsters, treasure and events. Read-aloud text is given exactly as printed.
> - **Describes only what the characters perceive.** It never states a hidden fact, a
>   monster's hit points, a DC, a trap or a secret door until the characters discover it.
> - **Adjudicates with the rules module**, citing `[p.N]` when asked or when a ruling is
>   unusual. Ambiguous rules get a ruling now, recorded in `House Rules.md`, and the
>   player may `/challenge` it.
> - **Rolls every die with the scripts.** Rolls the characters wouldn't know about use
>   `--secret`. Player rolls are made openly by the player or with `rpg-roll`.
> - **Keeps the world's state** with `rpg-gm state`, and records every improvised fact as canon.
>
> **What Claude does not do**
> - **No dice from its own head.** If a script fails, report the error and stop.
> - **No changing the adventure** to be easier, harder or more interesting. The dice fall
>   where they fall. That includes character death, and in a funnel it is the point.
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

The adventure is only fun if it's unspoiled. Claude must read it, and the player must not.

### 4.1 What we can and can't promise

This is **"nothing spoils you during normal play"**, not a security boundary. The player
owns the machine and can always open any file or expand any tool call. The design aims
to make sure the player never has to look away from anything they'd normally look at.

| Surface | Protection |
|---|---|
| Obsidian | All GM material lives under `.solo-rpg/`. Obsidian doesn't show dot-folders |
| Claude's replies | The contract forbids hidden facts. `/status` reads only player-known notes |
| Tool calls shown in Claude Code | Shown collapsed, but the **command line and file path are visible**. So ids are neutral (`a05`, `npc-03`, `m-02`, `ev-01`), never descriptive, and secret-roll labels are generic (`gm check`) |
| Tool results and subagent output | Collapsed by default. Minimised by the keeper (4.3). The player is told not to expand them during play |
| Claude's visible thinking | Unavoidable. The player is told not to open transcript view during play |
| Skill listings | Adventures are **not** skills, so their descriptions never appear in the skill list (section 5.1) |
| Build checkpoints | Spoiler-free summaries only (section 6) |

### 4.2 Player-known vs hidden

Two sets of records, never mixed:

- **Player-known**, in the Obsidian vault: character notes, session logs, a
  `Known/` folder of places, people and clues the party has actually learned, and
  handouts once they're found.
- **Hidden**, under `.solo-rpg/`: the adventure module, the world state, canon, the
  sealed roll log.

A fact moves from hidden to player-known only when the characters learn it in play. Claude
writes the player-known note at that moment, in the party's words ("the old woman said…"),
not the adventure's.

### 4.3 The keeper agent

Claude never opens adventure files directly during play. It asks the `keeper` agent, which
reads the relevant files plus the current state and returns a short, structured answer:

```
PERCEIVED   what the characters see, hear, smell now; read-aloud text verbatim, marked
BRIEF       only the hidden elements relevant to the declared action: what a search
            finds, who is lurking, which trigger fires, the rule/DC and rolls needed,
            monster ids to put in play
STATE       state changes this implies (for Claude to apply with rpg-gm)
CITES       [p.N] for each item
```

Why an agent rather than reading files: the transcript only ever holds the BRIEF for the
current action, not every secret in the area or adventure. It also keeps the main
conversation small for a long adventure. The keeper runs on a small model (it's retrieval
and filtering, not judgement), and it never narrates beyond PERCEIVED.

Claude may keep the current area's brief in context for the rest of the scene rather than
re-asking the keeper for every action.

## 5. Adventure modules

### 5.1 Where they live and why they aren't skills

```
<vault>/.solo-rpg/adventures/<adv-id>/
  adventure.yaml           manifest (5.2)
  overview.md              GM synopsis: background, factions, how it can end, hooks [p.N]
  areas/<area-id>.md       one per keyed area (5.3)
  npcs/<npc-id>.md         named NPCs: wants, knows, will say, stat ref (5.4)
  monsters/<mon-id>.yaml   stat blocks, structured for scaling (5.5)
  events/<ev-id>.md        triggers, timelines, countdowns (5.6)
  tables/<group>/*.yaml    wandering monsters etc., standard rpg-table format
  handouts/<h-id>.md       text given to the player when found, verbatim
  README.md  AUDIT.md      build log and audit (hidden)
```

Rules modules are skills because Claude should consult them automatically. An adventure
must be the opposite: Claude should never read it except through the keeper, and its
description would leak into the skill list. So adventures are plain data under
`.solo-rpg/`, and the play skills and keeper know where to find them.

Ids are neutral: `a<key>` for areas (`a05`, `a12b`), `npc-NN`, `m-NN`, `ev-NN`, `h-NN`.
Titles live inside the files, never in paths.

### 5.2 adventure.yaml

```yaml
id: adv-01                  # neutral; the title is below
title: "<as printed>"
system: dcc
requires: [dcc]             # rules module ids in this vault
sources: [{pdf: pdfs/<file>.pdf, offset: 2}]
party:                      # the adventure's own guidance, cited
  level: 0
  size: "15-20 0-level characters (4 per player)"
  source: "p.1"
scaling: []                 # the adventure's own scaling notes, if any, cited
start: a01
areas: [a01, a02, ...]
npcs: [npc-01, ...]
monsters: [m-01, ...]
events: [ev-01, ...]
clocks:                     # countdowns the adventure defines
  - {id: c-01, max: 6, source: "p.3"}
tables: [adv-01/wandering]
handouts: [h-01]
rules_used: [combat, crits-fumbles, luck, turn-unholy]   # rules topics the adventure calls on
```

### 5.3 Areas

```markdown
---
id: a05
key: "5"
title: "<as printed>"
source: "p.7"
exits:
  - {to: a04, via: "passage", dir: west, visible: true}
  - {to: a06, via: "secret door", dir: east, visible: false, find: "[p.7] search, DC 15"}
monsters: [{id: m-02, count: 4}]
events: [ev-02]
tables: []
---
## Read-aloud [p.7]
> Verbatim boxed text.

## Visible [p.7]
- What anyone looking around notices, beyond the boxed text.

## Hidden [p.7]
- Secrets, traps, concealed things, each with how it's found and what happens.

## Encounter [p.7]
- Who's here, what they're doing, how they react. Tactics as printed.

## Treasure [p.7]
- As printed.

## Triggers [p.7]
- "If <condition>, then <ev-02 / consequence>".
```

`exits` come from the key text first, then the map image where the key is silent. Each exit
the builder took from the map, rather than the text, is marked `from: map`. `rpg-gm check`
confirms every exit targets an existing area and every area is reachable from `start`.
That's the whole of "maps" in v1.

### 5.4 NPCs

Frontmatter `id, title, source, where, stat: m-NN`. Sections: **Wants**, **Knows** (each
secret tagged with what it would take to learn it), **Will say** (any printed dialogue,
verbatim), **Reaction** (as printed, or "use rules module reaction/morale").

### 5.5 Monsters

Structured, so scaling (section 11) is arithmetic:

```yaml
id: m-02
title: "<as printed>"
source: "p.7"
statline: "<verbatim stat line>"
fields: {init: 1, atk: "claw +2 melee (1d4)", ac: 12, hd: 2d8, hp: 9, mv: 30, act: 1d20,
         sp: "", sv: {fort: 1, ref: 0, will: 0}, al: C}
notes: "tactics, morale, special attacks, verbatim where mechanical"
```

`fields` keys are whatever the system's stat line uses (DCC's are shown).

### 5.6 Events

Anything time- or trigger-driven: `trigger` (area entered, flag set, clock value, time
passed), `effect`, `source`, and whether it's `once` or repeating. Countdown clocks the
adventure defines are in `adventure.yaml → clocks` and ticked with `rpg-gm`.

### 5.7 Page citations

Same rule as rules modules: every section and bullet carries `[p.N]` (printed page), so
the GM, the auditor and `/challenge` can check against the book.

## 6. Building an adventure

`/solo-rpg-gm:build-adventure <pdf> [adv-id]`, resumable via `BUILD-STATE.md` like
`build-module`. Staging goes in `.solo-rpg/staging/<adv-id>/`.

1. **Preconditions.** The required rules module exists in the vault (`rpg-gm` checks
   `requires`). If not, send the player to the forge first. For DCC, a rules module
   covering funnel character creation, combat, crits and fumbles, luck, and whatever the
   adventure's `rules_used` names is enough. The whole core book isn't required.
2. **Extract** with the forge's `pdf_extract.py`.
3. **Survey** (Claude reads everything) into `SURVEY.md`, which **the player does not
   read**. It lists areas, NPCs, monsters, events, tables, handouts, rules topics used,
   page offset and extraction risks.
4. **Spoiler-free checkpoint.** The player is shown only: title, page count, page offset,
   party guidance (level and size, usually on the cover), counts of areas / NPCs / monsters
   / tables / handouts, rules topics used, missing rules coverage, and extraction risks by
   page number. They approve or ask for changes to scope.
5. **Build** (parallel where possible):
   - `area-writer` agents, a batch of areas each, writing `areas/` and returning the
     monsters, NPCs, events and tables they reference.
   - Monsters, NPCs, events, overview and handouts, written by the main session.
   - Tables with the forge's `table-transcriber` agent, into the adventure's `tables/`.
   - `adventure.yaml`.
6. **Check.** `rpg-gm check <adv-id>`: ids resolve, every exit and table ref resolves,
   every area reachable, every section cited, `rpg-table validate` on its tables.
7. **Audit.** `adventure-auditor` spot-checks areas, stat blocks and tables against the
   pages (like `module-auditor`) and writes `AUDIT.md`. Claude fixes confirmed defects.
8. **Hand-off.** The player sees only counts: checks passed, defects found and fixed,
   anything unresolved by page number. Full `AUDIT.md` can be read after the adventure
   with `/reveal`.

Proof-reading by the player isn't possible without spoilers, so the auditor carries that
job. Accuracy matters less than for rules (the adventure is the GM's to interpret), but
stat blocks and tables are checked as strictly as a rules module's.

## 7. Campaign vault

`/solo-rpg-gm:gm-vault-setup "<campaign>" <rules-module-ids>`, run in the vault root.
Like `vault-setup`, it proposes before writing and adapts to an existing vault.

```
<vault>/
  pdfs/
  .claude/
    skills/dcc/ …                         rules module (from the forge)
    skills/gm-oracle/                     small oracle module (section 10)
    agents/rules-lawyer.md                campaign copy, as today
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
modules: [dcc, gm-oracle]
adventures:
  - {id: adv-01, status: active}       # planned | active | finished | abandoned
active_adventure: adv-01
party_mode: as-written        # section 11
open_rolls: true              # monster attacks and damage rolled in the open
session_log: summary          # summary | full
current_session: Sessions/Session 01.md
```

`settings.json` also allows `rpg-gm` and denies Claude edits to `sealed.jsonl` and to
`.solo-rpg/gm/**/state-log.jsonl`. `state.yaml` itself is changed only through `rpg-gm`,
so every change is logged.

Several adventures per campaign: characters, `Known/` and sessions carry across. Each
adventure has its own module and its own `gm/<adv-id>/` state. `/adventure` switches the
active one, lists them, or marks one finished.

## 8. Hidden state

`.solo-rpg/gm/<adv-id>/state.yaml`:

```yaml
current_area: a05
time: {turns: 14, source_unit: "10-minute turns"}
areas:   {a01: explored, a05: entered}
monsters:                 # instances, created when put in play
  m-02#1: {area: a05, hp: 5, status: active}
  m-02#2: {area: a05, hp: 0, status: dead}
npcs:    {npc-01: {status: alive, disposition: wary, met: true}}
flags:   {ev-02: fired}
clocks:  {c-01: 2}
treasure_taken: [a03/1]
```

`canon.md` records every improvised fact (section 10), with session and scene, so
improvisation stays consistent across sessions.

`rpg-gm` (in the new plugin):

| Command | Does |
|---|---|
| `rpg-gm state show [path]` | Print state (Claude only; never shown to the player) |
| `rpg-gm state set <path> <value> --why "<ref>"` | Change a value; logs old → new to `state-log.jsonl` |
| `rpg-gm spawn <mon-id> [--count N] [--area a05]` | Create monster instances, rolling hp with `rpg-roll --secret` unless fixed |
| `rpg-gm damage <instance> <n>` / `tick <clock> [n]` | Common shortcuts, logged |
| `rpg-gm canon "<fact>" --basis "<why>"` | Append to `canon.md` |
| `rpg-gm check <adv-id>` | Validate an adventure module (section 6) |
| `rpg-gm reveal [adv-id]` | Print the sealed log and verify it against the audit hashes (section 12) |

Output mentions only neutral ids, so the collapsed tool call in the UI stays spoiler-free.

## 9. Playing

### 9.1 Commands (v1)

| Command | Does |
|---|---|
| `/solo-rpg-gm:start` | New session note; recap from player-known notes only; resume in the current area (the keeper reads it) |
| (plain messages) | The player's actions. This is the whole game loop (9.2) |
| `/solo-rpg-gm:status` | Party sheets, what the party knows, open leads. Player-known only |
| `/solo-rpg-gm:recap [n]` | Recap of the last n sessions from the session notes |
| `/solo-rpg-gm:challenge` | The rules lawyer reviews the last ruling against the rules module and house rules. If it disagrees with a citation, the GM corrects the ruling. If the rules are ambiguous, the player decides and it's recorded in `House Rules.md` |
| `/solo-rpg-gm:end` | Close the session: summary to the session note, player-known notes updated, state saved, loose ends (as the party knows them) listed |
| `/solo-rpg-gm:adventure` | List, start, switch or finish adventures |
| `/solo-rpg-gm:reveal` | After an adventure is finished: sealed rolls, unexplored areas, what was missed, `AUDIT.md`. Asks for confirmation; refuses on an active adventure unless forced |

Character creation uses the rules module's own procedure runner (e.g. `/dcc-funnel`),
built by the forge, so it's not duplicated here.

### 9.2 The loop

For each player message:

1. **Understand the action.** If it's unclear what the characters are doing, ask. Never
   fill in a PC's action.
2. **Consult.** Entering an area, searching, interacting with a feature or starting a
   conversation → keeper. Otherwise use the scene brief already in context.
3. **Resolve.** Apply the rules module. Player rolls are asked for ("roll a Luck check")
   and made with `rpg-roll` or physical dice. GM rolls use `rpg-roll`, `--secret` if the
   characters wouldn't see them. Monster attacks and damage follow `open_rolls`.
4. **Improvise if needed** (section 10).
5. **Narrate** the outcome (9.4).
6. **Record.** `rpg-gm` for hidden state; character notes for HP, luck, deaths and gear
   (player-known, so written openly); `Known/` for what the party learned; one or two
   lines in the session note.

Out-of-character questions start with "OOC:". The GM answers rules questions, can remind
the player of anything the party knows, and refuses anything else.

### 9.3 Combat

Initiative, actions and results come from the rules module. Monster instances come from
`rpg-gm spawn`. Hidden hp is tracked in state and never stated. Descriptions indicate
condition in the fiction ("it staggers"). Morale follows the adventure, then the rules
module. PC death is final unless the rules module provides a way back (DCC's "recover the
body" and Luck rules, for instance).

### 9.4 Default narration style

- Second person plural, present tense ("You see…").
- Read-aloud text verbatim, as a blockquote, before anything else.
- Otherwise 2–5 sentences: what changed, what's now apparent, what's pressing. No purple
  prose, no inner thoughts for the PCs, no hints about hidden things.
- Mechanics after the fiction, in one line: the roll and its result, and state changes the
  party would know about ("Gurney takes 3 damage, 1 hp left").
- End on the situation, not on a menu of options. Ask "what do you do?" only when it's
  unclear whose turn it is.

Personality and voice are for a later version (section 14).

## 10. Improvisation and the oracle

Every question the adventure doesn't answer is resolved by this ladder, in order:

1. **The adventure says.** Use it, cited.
2. **The rules module says** (reaction, morale, random encounters, searching). Use it.
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

**The oracle.** `gm-vault-setup` writes a tiny rules module `gm-oracle` into the vault:
one original yes/no table by likelihood (with "yes, and" / "no, but" results) and one
original "which way does it go" table for NPC attitude. Both are ours, not copied from
any published solo engine. It's replaceable later by any solo-engine module the player
prefers.

## 11. Party and balance

`party_mode` in `solo-rpg.yaml`:

| Mode | v1? | Meaning |
|---|---|---|
| `as-written` | yes | Use the adventure's party guidance. The player controls the whole party. For a DCC funnel this is the intended experience: several 0-level characters each |
| `scaled` | later | Apply the adventure's own scaling notes (`adventure.yaml → scaling`), or the rules module's, to monster counts and hp when spawned |
| `dm-yourself` | later | One PC plus a sidekick, 2 levels above the adventure's level, max hp; monster hp and counts × ¾. Applied by `rpg-gm spawn` so the adventure data stays unmodified |

Scaling always happens at spawn time and is recorded on the instance (`scaled: 0.75`),
never by editing the adventure module.

## 12. Changes to solo-rpg-core and solo-rpg-forge

Small, and compatible with the clerk style:

1. **`rpg-roll --secret` and `rpg-table roll --secret`.** The full result is appended to
   `.solo-rpg/sealed.jsonl` and printed to stdout (the GM needs it). `audit.jsonl` gets a
   stub `{type, secret: true, label, sha256}` with the hash of the sealed record, so the
   sealed log can be checked for tampering at `/reveal`. `--log` writes "GM rolled (hidden)
   — <label>" to the session note.
2. **Adventure tables.** `common.module_dirs()` also finds
   `.solo-rpg/adventures/*/tables` when called with `--gm` (or `SOLO_RPG_GM=1`).
   `rpg-table list` without `--gm` never shows adventure tables.
3. **Forge.** No behaviour change. `build-adventure` calls its `pdf_extract.py` and
   dispatches its `table-transcriber` agent. `module_tool.py` does not gain an `adventure`
   kind; adventures have their own spec and tool.
4. **README.** The marketplace intro stops saying "Claude is never the GM" globally, and
   instead describes the two styles and which plugins each uses.

## 13. Milestones

| # | Deliverable | Done when |
|---|---|---|
| M0 | This design | Reviewed and agreed |
| M1 | Core changes (section 12.1–12.2) | Secret rolls, sealed log, hash check, hidden adventure tables all work from the CLI |
| M2 | Adventure spec + `rpg-gm check` + `build-adventure` + `area-writer` + `adventure-auditor` | A small DCC adventure builds, checks clean and audits, with only spoiler-free output shown |
| M3 | `gm-vault-setup`, GM contract, `gm-oracle` module | A fresh vault with the `dcc` rules module is set up for GM play |
| M4 | `keeper`, `rpg-gm` state commands, play skills | A full session can be played, ended and resumed |
| M5 | Playtest the funnel end to end | Notes on what broke, fed back into the spec |
| Later | `scaled` and `dm-yourself` party modes, GM personality, better map handling | — |

## 14. Open questions

1. **Which adventure?** A specific small DCC funnel to test against. Its structure should
   be checked against section 5 before M2.
2. **Command names.** Plugin-namespaced (`/solo-rpg-gm:start`) as proposed, or
   `gm-vault-setup` also writing short vault-local wrappers (`/start`, `/end`) like
   `session-kit` does.
3. **Open or secret monster rolls** by default (`open_rolls`). Proposed: open, so the
   player sees the dice that hurt them.
4. **Session log detail** (`session_log`). Proposed: a summary per scene plus every open
   roll, not a full transcript.
5. **DCC rules module scope.** The core book is large. Proposed: build only funnel
   creation, combat, crits and fumbles, luck, and what the adventure's `rules_used` names,
   then extend as later adventures need more.
6. **Keeper model.** Proposed: a small, fast model. Needs checking in M4 that it filters
   reliably without leaking or dropping relevant secrets.
