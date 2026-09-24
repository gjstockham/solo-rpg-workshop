---
name: ingest
description: First stage of building a solo-rpg ruleset module. Extracts a rulebook PDF into a staging folder (text by page, table candidates, page renders, headings) and writes a SURVEY of chapters, tables, procedures and trackable state for the player to approve. Use when the player wants to turn a rulebook, solo engine, supplement or setting PDF into a module, or says "ingest", "import this book" or "extract the rules".
argument-hint: "<path/to/book.pdf> [module-id]"
disable-model-invocation: true
allowed-tools:
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/*)
---

# Ingest a rulebook

Goal: a staging folder, plus a `SURVEY.md` the player approves before any module is built.
Nothing in this stage is final. It's a map of the book, and it's cheap to redo.

Input: $ARGUMENTS (PDF path, optional module id).

## 0. Preconditions

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/module_tool.py" where` to find the workshop
  root and staging folder. Use `python` if `python3` isn't available.
- Check the dependencies: `python3 -c "import pdfplumber, pypdf, yaml"`. If they're missing,
  show `pip install pdfplumber pypdf pyyaml` and stop.
- Agree on three things with the player in one short exchange. Offer your best guess for each
  so they can just confirm:
  1. **Module id** (kebab-case, short; it becomes the plugin namespace).
  2. **Kind**: `game`, `solo-engine`, `supplement` (needs a base module) or `setting`.
  3. **One module or several.** A core book plus its supplement can be one module, or the
     supplement can be its own module with `requires:`. Default to separate modules when the
     books are sold separately, so each can be reused in other combinations.

## 1. Extract

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_extract.py" "<pdf>" --out "<staging>/<module-id>/<book-slug>"
```

Useful options: `--pages 1-60` (trial run on a big book), `--columns 2` (force two columns
if auto-detection misses), `--render all` (render every page, for layout-heavy books).

Read `REPORT.md`. If there are scanned (image-only) pages, tell the player and stop.
OCR comes first. For a handful of pages you can offer to transcribe them from `images/`.

## 2. Establish page numbering

Citations use the book's **printed** page numbers, because that's what the player sees on
paper and in the PDF footer. Compare several `pages/pNNNN.txt` files (footers and headers)
with the manifest's `printed` labels. Work out the offset, whether it's constant, and any
unnumbered sections. Record the result in the survey. If you're unsure, look at two page
images.

## 3. Survey the book

Use `outline.json` (bookmarks) if present, otherwise `headings.md`. Skim `text.md` by chapter.
Don't read everything in depth; this is triage. Write
`<staging>/<module-id>/SURVEY.md`:

```markdown
# Survey: <title>  (module: <id>, kind: <kind>)
Source PDF: <filename> — <N> pages — printed = PDF − <offset> (<notes>)

## Chapters
| # | Chapter | PDF pages | Printed | Category | Plan |
Category: rules | procedure | tables | lore/setting | example-of-play | adventure | GM-advice | reference-sheet | front/back matter
Plan: rules file(s) to write, or "skip", or "lore (condensed)"

## Tables (<count>)
| Title as printed | Printed page | Dice | ~Rows | Complexity | Notes |
Complexity: simple | multi-column | nested/then | two-dice grid | spans pages | irregular

## Procedures
| Procedure | When | Pages | Notes |

## Trackable state
Records (sheet-like things with fields), trackers (numbers that change in play, with min/max),
lists (things the rules tell you to maintain) — each with page.

## Dice conventions
Dice used; roll-over/under; ties; doubles; special results — with pages.

## Risks
Scanned pages, bad table extraction (compare tables/*.csv with images/), two-column
interleaving, sidebars, errata the player should apply, content that is ambiguous.
```

Guidance:
- Look at the page images for every table-heavy page before judging complexity. The CSV
  candidates are often wrong on merged cells and multi-page tables.
- A table with dice ranges is a **table**. A chart consulted by value (costs, ranges,
  equipment stats) is **reference data** for a rules file, not a table.
- "Roll on the table in chapter X" references are useful. Note them, because they become `then:` links.
- Default plan for adventures and examples of play: skip. For lore: condensed. The player can override.

## 4. Checkpoint

Present a short summary: chapter count by category, table count with the complex ones named,
procedures, trackers and lists, and risks. Ask the player to confirm or adjust the plan.
Save any changes they make to SURVEY.md. Then point them to the next step:
`/solo-rpg-forge:build-module <module-id>`.

Do not start building in this skill. A clean hand-off keeps big books resumable across sessions.
