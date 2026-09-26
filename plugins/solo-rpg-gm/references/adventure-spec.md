# Adventure module specification

An **adventure module** is one published adventure, built as hidden data inside the
player's vault so that Claude can run it as GM. It holds the adventure's facts only. The
rules come from a **rules module** built by solo-rpg-forge (`.claude/skills/<rules-id>/`),
and all dice and table code lives in solo-rpg-core.

The player shouldn't read an adventure module. Everything here is written for Claude and
its agents, and everything shown to the player while building one must be spoiler-free
(section 8).

## Contents
1. Layout
2. Ids
3. adventure.yaml
4. Element types
5. Element files
6. Stat blocks
7. Tables, clocks, overview and index
8. Spoiler discipline while building
9. Size and style

## 1. Layout

```
<vault>/.solo-rpg/adventures/<adv-id>/
  adventure.yaml             manifest (section 3)
  overview.md                GM synopsis (section 7)
  INDEX.md                   every element: id, type, title, pages, one line (section 7)
  rules.md                   optional: rules the adventure itself adds (section 7)
  <type>/<id>.md             one file per element, for each type in use (sections 4-5)
  stat-blocks/<id>.yaml      stat blocks (section 6)
  tables/<group>/<id>.yaml   random tables, standard rpg-table format (section 7)
  README.md                  sources, build log, known gaps
  AUDIT.md                   written by the adventure-auditor agent
<vault>/.solo-rpg/staging/<adv-id>/
  book/                      rpg-gm extract output (pages/, images/, text.md, ...)
  SURVEY.md  BUILD-STATE.md
```

Adventures are **not** skills. Claude reaches them deliberately (through the keeper
agent during play), and their contents never appear in the skill list. Obsidian doesn't
show `.solo-rpg/`, so the player won't come across them in the vault either.

`rpg-gm where` prints the paths. `rpg-gm scaffold` creates the folder, and `rpg-gm check`
lints it.

## 2. Ids

Tool calls are visible in Claude Code even when collapsed, so ids must not give anything
away. An id is a **type prefix, a hyphen and a number**, optionally followed by letters or
digits: `loc-05`, `loc-12b`, `npc-03`, `stat-01`. Never `loc-crypt` or `npc-traitor`.

- Where the book keys something (area 12b), put the key in the id: `loc-12b`.
- Otherwise number in order of first appearance: `npc-01`, `npc-02`.
- Tables are `tbl-NN`, clocks `clk-NN`.
- The adventure id itself can be anything kebab-case. The player chose the adventure, so
  its title isn't a secret. `rpg-gm scaffold` defaults to `adv-NN`.

Titles live inside the files, never in paths, command lines or tool output.

## 3. adventure.yaml

Created by `rpg-gm scaffold`. Fields:

| Field | Holds |
|---|---|
| `id`, `title` | id (matches the folder) and the title as printed |
| `requires` | rules module id(s) in this vault |
| `sources` | `file` (PDF name) and `page_offset` (printed = PDF − offset) |
| `structure` | `site-based`, `event-driven`, `investigation`, `scene-based` or `mixed` |
| `party` | `guidance` (the book's party size, level or makeup, as printed) and `source` |
| `scaling` | the book's own notes on adjusting for party size or strength: `[{note, source}]` |
| `start` | `element` (where play begins), `note` (how, as printed), `source` |
| `types` | element types beyond section 4's vocabulary: `{name: prefix}` |
| `elements` | `{type: [ids]}` for every type in use |
| `clocks` | countdowns, timelines or tracks the adventure defines: `[{id, max, source, note}]` |
| `tables` | ids of this adventure's tables |
| `rules_topics` | rules the adventure calls on, named as the rules module's INDEX names them |

## 4. Element types

The survey decides which types an adventure needs. This vocabulary keeps similar
adventures alike; add a type only when none of these fits, and declare it under
`types:` with its own prefix.

| Type | Prefix | Typical source | Holds |
|---|---|---|---|
| `locations` | `loc` | keyed areas, sites, rooms, regions | what's perceived, what's hidden, who's here, treasure, triggers, connections |
| `npcs` | `npc` | named or significant characters | how they appear, wants, knows, printed dialogue, reaction, stat block |
| `stat-blocks` | `stat` | monster and NPC statistics | the stat line verbatim plus structured fields (section 6) |
| `events` | `ev` | timelines, triggered scenes, reinforcements, random events | trigger, effect, once or repeating |
| `clues` | `clue` | investigation adventures | what it reveals, where it can be found |
| `scenes` | `scn` | scene- or chapter-based adventures | how it opens, what's at stake, how it can end, where it leads |
| `factions` | `fac` | groups with goals | goals, resources, what they do if left alone |
| `items` | `itm` | unique or magic items, artefacts | how it looks, what it does, how that's learned |
| `handouts` | `h` | player handouts | the text as given to players, verbatim |

Things that are **not** elements: generic treasure lists (a location's `## Treasure`),
maps (connections, section 5), random tables (section 7), and rules the book repeats
from the core rules (cite the rules module instead).

## 5. Element files

Markdown with YAML frontmatter, one per element, at `<type>/<id>.md`.

### Frontmatter

Every element has `id`, `title` (as printed) and `source` (`"p.7"` or `"p.7-8"`, printed
pages). References to other elements always use ids. Type-specific keys:

| Type | Keys |
|---|---|
| `locations` | `key` (as printed), `connections`, `entry`, `encounters`, `npcs`, `items`, `events`, `tables` |
| `npcs` | `where` (location id), `stat` (stat block id), `faction` |
| `events` | `trigger` (short text), `where`, `once` (true/false), `clock` |
| `clues` | `found_at` (ids), `leads_to` (ids) |
| `scenes` | `where`, `leads_to` |
| `factions` | `members`, `base` |
| `items` | `where` |
| `handouts` | `found_at` |

Only include keys that apply. Custom types use the keys that make sense and ids for
references.

**connections** (locations): where the location leads.

```yaml
connections:
  - {to: loc-04, via: "<as printed>", visible: true}
  - {to: loc-06, via: "<as printed>", visible: false, find: "<how it's found, as printed> [p.7]"}
  - {to: loc-09, via: "<as printed>", oneway: true}
  - {to: loc-10, via: "<as printed>", from: map}
```

Take connections from the text first. Use the map images only where the text is silent,
and mark those `from: map`. Record each connection **in both locations**, so every file
is complete on its own (the keeper reads one location at a time); the two sides can
differ, as with a door that's hidden from one side only. A way that can only be taken
one way (a chute, a collapsing bridge) is recorded on the side it leaves from, with
`oneway: true`. `visible: false` means the characters don't see the way until they find it,
and it needs a `find:`. A location that play can reach without a connection (the start of
a second chapter, a teleport destination, somewhere an event moves the party) gets
`entry: true`, so `rpg-gm check` doesn't report it unreachable.

**encounters** (locations): `[{stat: stat-02, count: 4}]`. `count` is a number or a dice
expression as printed (`"1d4+1"`). Add `note:` for anything the entry says about them
(asleep, only at night).

### Sections

`##` headings, each with at least one `[p.N]`, and every bullet or paragraph starting with
its own `[p.N]`. Use these section names for the standard types, in this order, and leave
out any that don't apply:

| Type | Sections |
|---|---|
| `locations` | Read-aloud, Visible, Hidden, Encounter, Treasure, Triggers |
| `npcs` | Appearance, Wants, Knows, Will say, Reaction |
| `events` | Trigger, Effect |
| `clues` | Reveals, Found |
| `scenes` | Opening, Stakes, Outcomes |
| `factions` | Goals, Resources, If left alone |
| `items` | Appearance, Powers |
| `handouts` | Text |

**What the characters can perceive.** Only **Read-aloud**, **Visible**, **Appearance** and
**Text** sections describe what the characters perceive without doing anything. Every
other section is GM-only. The keeper relies on this, so anything the characters would
only learn by searching, asking, fighting or luck belongs in a GM-only section, with how
it's learned:

- **Hidden**: each secret with how it's found (the check, the action, the condition) and
  what happens.
- **Knows**: each thing the NPC knows, with what it takes to get it out of them.
- **Powers**: what the item does and how that's discovered.

**Read-aloud** is a blockquote, verbatim, including the book's own line breaks where they
matter. If the book has no boxed text for the element, leave the section out rather than
writing one. **Will say** and handout **Text** are verbatim too, in quotation marks.

**Faithful, not flavourless.** Keep every number, name, condition, trigger and
consequence. Condense GM advice and repeated description. Quote verbatim where the text
is itself mechanical (a trap's effect, an item's power) or will be read to the player.
Omit art captions and designer's notes unless they change how the adventure runs.

Example:

```markdown
---
id: loc-05
title: "<as printed>"
key: "5"
source: "p.7"
connections:
  - {to: loc-04, via: "<as printed>", visible: true}
  - {to: loc-06, via: "<as printed>", visible: false, find: "<as printed> [p.7]"}
encounters: [{stat: stat-02, count: 4, note: "<as printed>"}]
events: [ev-02]
---
## Read-aloud [p.7]
> Verbatim boxed text.

## Visible
- [p.7] What anyone looking around notices, beyond the boxed text.

## Hidden
- [p.7] A secret: how it's found → what happens.

## Encounter
- [p.7] Who's here, what they're doing, how they react. Tactics as printed.

## Treasure
- [p.7] As printed.

## Triggers
- [p.7] If <condition>, then ev-02.
```

## 6. Stat blocks

YAML, one per stat block, at `stat-blocks/<id>.yaml`. A stat block printed once and used
in several places is one element. The same creature printed with different statistics in
two places is two elements.

```yaml
id: stat-02
title: "<as printed>"
source: "p.7"
statline: "<the stat block verbatim>"
fields:            # structured, named after the rules module's stat-block fields
  hp: 9
hp_roll: "2d8"     # only if the book gives hit dice rather than fixed hit points
notes: "tactics, morale and special abilities, verbatim where mechanical"
```

**fields**: if the rules module's `module.yaml` has a record for creatures or stat
blocks, use its field names. Otherwise use the stat line's own labels in kebab-case, the
same names in every stat block of the adventure. `hp` is a whole number. If the book gives
hit dice, put the expression in `hp_roll` and leave `hp` out (or give the average if the
book prints one). Keep attack, damage and defence numbers exact.

## 7. Tables, clocks, overview and index

**Tables.** Standard rpg-table files (`rpg-table schema`) at `tables/<group>/<id>.yaml`,
with ids `tbl-NN` and `source: {book: <adv-id>, page: <printed page>}`. The book field is
the adventure id so no title shows up in tool output. `then:` can point to a rules
module's table as `<rules-id>/<table-id>`. Adventure tables are only visible to
`rpg-table` with `--gm`: `rpg-table validate --gm <file>`, `rpg-table roll <adv-id>/tbl-01
--gm --secret`.

**Clocks** live in `adventure.yaml` only: `{id: clk-01, max: 6, source: "p.3", note: "what
it counts and what happens when it fills"}`. Add an event for what happens when a clock
fills, with `clock: clk-01`.

**overview.md**: the GM synopsis, every paragraph cited. Background, what's really going
on, factions in brief, how play begins, the ways it can end, and anything the GM must know
before play (the book's own advice on running it, condensed). It's what the GM reads
before the first session and what the keeper uses for context.

**INDEX.md**: one row per element, table and handout: `| id | type | title | pages | one
line |`. The one line says what it's for in play ("guard room; alarm raises ev-02"). The
keeper and the GM find things through this.

**rules.md** (optional): rules the adventure itself introduces (a hazard, a special
combat situation, a new spell or condition), in the forge's rules-file format:
`[p.N]` on every paragraph, verbatim where mechanical. Rules the book repeats from the
core game are not copied; cite the rules module instead.

## 8. Spoiler discipline while building

The player runs the build, so they see Claude's messages and the collapsed tool calls.

- Messages to the player name elements by **id and page only**: "writing loc-01 to loc-08
  (p.4-9)", never titles, names or contents.
- Checkpoints and hand-offs give **counts**, the structure, the party guidance, uncovered
  rules topics and page numbers. Nothing else from the adventure.
- Agents' final messages use ids and pages, not content.
- Labels on any roll made while building are generic.
- If the player asks about the content, remind them it's a spoiler and ask them to
  confirm before answering.

## 9. Size and style

- An element file should stay under about 150 lines. Split a sprawling location into
  sub-locations (`loc-12`, `loc-12a`, `loc-12b`) connected to each other.
- `overview.md` should stay under about 200 lines.
- Every section, bullet, stat block, table and clock has a page reference. `rpg-gm check`
  enforces most of this.
