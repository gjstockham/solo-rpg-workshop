---
name: build-adventure
description: Second stage of building a solo-rpg GM adventure module. Turns an approved adventure SURVEY into a hidden, page-cited adventure module (locations, NPCs, stat blocks, events and whatever else the survey found, plus validated tables), checks and audits it, and reports to the player without spoilers. Use after /solo-rpg-gm:ingest-adventure, or when resuming or repairing a partly built adventure.
argument-hint: "<adventure-id>"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
  - Bash(rpg-table *)
---

# Build an adventure

Adventure: $ARGUMENTS. Read `${CLAUDE_PLUGIN_ROOT}/references/adventure-spec.md` first. It
defines every file you'll produce.

Everything is written into the player's **vault**, never into this plugin. Run `rpg-gm
where` for the paths. The adventure lives at `<vault>/.solo-rpg/adventures/<adv-id>/` and
staging at `<vault>/.solo-rpg/staging/<adv-id>/`.

Subagents can't expand `${CLAUDE_PLUGIN_ROOT}`, so pass them absolute paths: the adventure
dir, the staging book dir (`<staging>/book`) and this plugin's root (the `gm plugin:` line
of `rpg-gm where`).

You'll run this adventure as GM later, from these files alone. **A dropped trigger,
secret or stat becomes a mistake at the table**, so accuracy beats speed.

**No spoilers.** The player watches this build. Every message follows adventure-spec §8:
ids, counts and page numbers only. Tell agents the same.

## Resumability

Keep `<staging>/BUILD-STATE.md` as a checklist with one line per element batch, table
group, and the overview/index/manifest steps: `[ ]` todo, `[~]` in progress, `[x]` done.
Update it after every unit. On start, if it exists, report progress (ids and counts only)
and continue from the first unfinished item. Don't redo finished work unless asked.

## Steps

### 1. Scaffold
Needs an approved `<staging>/SURVEY.md`. If it's missing, send the player to
`/solo-rpg-gm:ingest-adventure`.
```
rpg-gm scaffold <adv-id> --title "<title>" --requires <rules-id> --types <types from the survey>
```
Then fill in `adventure.yaml` from the survey: `sources`, `structure`, `party`, `scaling`,
`start`, any custom `types`, every planned id under `elements`, `clocks`, `tables` and
`rules_topics`. Create BUILD-STATE.md from the survey's batches.

### 2. Elements (parallel)
Dispatch the **element-writer** agent once per batch in the survey, three or four at a
time. Each call passes:
- adventure id and dir, staging book dir, plugin root, page offset;
- the batch name from BUILD-STATE.md (`b01`, `b02` ...) and its elements: id, type,
  key/title and printed pages;
- the **whole Elements, Stat blocks, Tables and Clocks lists from the survey**, so
  references use the right ids;
- the stat-block field names from the survey, so every stat block uses the same ones;
- the map pages, for connections the text doesn't give;
- which stat blocks this batch owns (the batch covering the page where each is printed).

Each agent returns the files it wrote, the references it found and anything unplanned.
For unplanned elements, assign ids, add them to SURVEY.md and `adventure.yaml`, and
dispatch them as a new batch. Each agent writes its INDEX rows to
`<staging>/index/<batch>.md`. For each reported cross-batch connection, check the other
side once both batches are done.

### 3. Tables (parallel)
Group the survey's tables by section and dispatch solo-rpg-forge's **table-transcriber**
agent for each group, with: the adventure id as the module id, the adventure dir as the
module dir, the staging book dir, the output folder `<adventure dir>/tables/<group>/`, and
the tables (id, title, printed page, PDF page, dice, notes). Tell it:
- use the `tbl-NN` ids from the survey, and `source: {book: <adv-id>, page: <printed page>}`;
- validate with `rpg-table validate --gm <file>` (adventure tables are only visible with `--gm`);
- a `then:` to a rules module table is written `<rules-id>/<table-id>`;
- report by id and page only, per adventure-spec §8.

### 4. Overview, rules and index
Write these yourself, since they need the whole picture:
- `overview.md` (adventure-spec §7), from the survey and the element files.
- `rules.md`, if the survey lists rules the adventure adds.
- Any clock's end event, if an element batch didn't cover it.
- `INDEX.md`: one row per element and table, merged from `<staging>/index/*.md` plus a row
  per table, in id order.

### 5. Check
```
rpg-gm check <adv-id>
```
Fix every error and re-run until it reports OK. Understand every warning: an unreachable
location may need `entry: true`, a one-sided connection may need its other side, an
unlisted file may be an unplanned element.

### 6. Audit
Dispatch the **adventure-auditor** agent with the adventure id, adventure dir, staging
book dir and plugin root. It spot-checks the module against the pages and writes
`AUDIT.md`. Fix every confirmed defect. For systematic errors (a whole batch misreading
two-column text, stat fields consistently wrong), redo that unit. Re-run `rpg-gm check`.

### 7. README
Update `<adventure dir>/README.md`: source PDF and offset, build date, known gaps, and the
audit's summary.

### 8. Hand-off
Tell the player, spoiler-free:
- that the adventure is built: counts per element type, stat blocks, tables, clocks;
- the check result and the audit result (defects found and fixed, anything unresolved by
  page number);
- rules topics the rules module still doesn't cover, and whether that matters before
  play (extend the rules module with the forge if so);
- that `AUDIT.md` and everything else stay hidden until they choose to look after play;
- the next step: if the vault isn't set up for GM play yet (`rpg-gm status`), that's
  `/solo-rpg-gm:gm-vault-setup`. If it is, run `rpg-gm init` now to register the new
  adventure as `planned`.

## Quality bar (check before hand-off)
- Every element in the survey exists, and `rpg-gm check` reports OK.
- Every read-aloud passage is verbatim, and nothing the characters would have to find out
  is in a Read-aloud, Visible, Appearance or Text section.
- Every stat block's numbers match the book, and every encounter points to one.
- Every table validates, and every clock has an event for when it fills.
- No message to the player named an element, a title or anything from the adventure's
  content.
