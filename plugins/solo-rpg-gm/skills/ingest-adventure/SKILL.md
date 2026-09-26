---
name: ingest-adventure
description: First stage of building a solo-rpg GM adventure module. Extracts a published adventure PDF into a hidden staging folder and writes a private SURVEY of its structure, elements, stat blocks, tables and rules needs, then shows the player a spoiler-free summary to approve. Use when the player wants Claude to run a published adventure, or says "ingest this adventure" or "import this module for GM play".
argument-hint: "<path/to/adventure.pdf> [adventure-id]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
  - Bash(rpg-table *)
---

# Ingest an adventure

Goal: a staging folder and a private `SURVEY.md` mapping everything in the adventure,
approved (in spoiler-free form) by the player before anything is built. Input: $ARGUMENTS.

**The player intends to play this adventure, so don't spoil it.** Follow
`${CLAUDE_PLUGIN_ROOT}/references/adventure-spec.md` §8 in every message: ids, counts and
page numbers only; never titles, names, plot or contents.

## 0. Preconditions

- Check the dependencies: `python3 -c "import pdfplumber, pypdf, yaml"`. If they're
  missing, show `pip install pdfplumber pypdf pyyaml` and stop.
- Run `rpg-gm where` and use its paths. Everything goes in the player's **vault**, never in
  this plugin. Confirm it's the vault they mean; if not, they need to `cd` there and
  restart Claude Code.
- **A rules module is required.** `rpg-gm where` lists the rules modules built here. If
  there's none for the adventure's game, stop and send the player to
  `/solo-rpg-forge:ingest` and `/solo-rpg-forge:build-module` for the rulebook first.
- Agree two things in one short exchange, offering your best guess for each:
  1. **Adventure id**: kebab-case. The next free `adv-NN` is the default; a short form of
     the title is fine too, since the player already knows what they're playing.
  2. **Rules module**: which built rules module this adventure is for.

## 1. Extract

```
rpg-gm extract "<pdf>" <adv-id>
```

This runs solo-rpg-forge's extractor into `.solo-rpg/staging/<adv-id>/book/` and renders
every page to `images/` (boxed text, stat blocks and maps are easier to read from the
image). Options pass through: `--pages 1-20` for a trial, `--columns 2` if two-column
detection misses.

Read `REPORT.md`. If there are scanned (image-only) pages, tell the player the page
numbers and stop; OCR comes first. For a handful of pages you can offer to transcribe from
`images/` instead.

## 2. Page numbering

As the forge's ingest does: compare several `pages/pNNNN.txt` footers with the manifest's
`printed` labels, work out the offset and any unnumbered pages, and record it in the
survey. Look at two page images if unsure.

## 3. Survey

Unlike a rulebook, read the **whole adventure**: every element must be found and given an
id before building. Work from `text.md` and check `images/` wherever layout matters (boxed
text, sidebars, stat blocks, maps, handouts, tables).

Read the rules module's `reference/rules/INDEX.md` and `module.yaml` too, to see which
rules topics it covers and whether it defines stat-block fields.

Write `.solo-rpg/staging/<adv-id>/SURVEY.md`:

```markdown
# Survey: <title>  (adventure: <adv-id>, rules: <rules-id>)
Source PDF: <filename> — <N> pages — printed = PDF − <offset> (<notes>)
Structure: <site-based | event-driven | investigation | scene-based | mixed> — why, one line
Party guidance: <as printed> [p.N]            (or "none given")
Scaling notes: <as printed> [p.N]             (or "none")
Start: <how play begins, which element> [p.N]

## Sections
| # | Section | PDF pages | Printed | Category | Plan |
Category: background | player-intro | locations | npcs | events | scenes | clues | encounters |
          stat-blocks | tables | handouts | maps | new-rules | GM-advice | front/back matter
Plan: element batch(es) | overview | rules.md | skip

## Element types
| Type | Prefix | Count | Notes |
Standard vocabulary: adventure-spec §4. Propose a new type only if none fits.

## Elements
| Id | Type | Key / title | Printed pages | Batch | Notes |
Every location, NPC, event, clue, scene, faction, item and handout, with its final id
(adventure-spec §2). Batches: about 8-15 elements or 12 pages each, grouped by page order.

## Stat blocks
| Id | Title | Printed page | Used by | Notes (hit dice vs fixed hp, odd format) |
Stat-block fields: <the field names every stat block will use; from the rules module's
module.yaml if it defines them, else from the stat line's labels>

## Tables
| Id | Title as printed | Printed page | Dice | ~Rows | Complexity | Notes |

## Clocks
| Id | What it counts | Max | Printed page |

## Maps
| Printed page | Shows | Keyed? | Connections the text doesn't give |

## Rules topics
| Topic (as the rules module names it) | Covered? (rules file) | Where the adventure uses it |

## New rules in the adventure
Hazards, conditions, spells or subsystems the adventure itself defines → rules.md.

## Risks
Scanned pages, bad extraction, two-column interleaving, stat blocks in an unusual format,
connections only on the map, ambiguities, errata.
```

## 4. Spoiler-free checkpoint

Show the player **only**:
- title, page count and page offset;
- the structure (one word) and the party guidance as printed;
- counts per element type, and the number of stat blocks, tables, clocks and handouts;
- rules topics the rules module doesn't cover, by the rules module's name for them, and
  whether you suggest extending the rules module first;
- extraction risks by page number.

Ask them to confirm, or to adjust the scope (for example, skip an appendix). Save any
changes to SURVEY.md. Then point them to `/solo-rpg-gm:build-adventure <adv-id>`.

Don't start building in this skill. A clean hand-off keeps big adventures resumable.
