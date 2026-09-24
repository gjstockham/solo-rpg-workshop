---
name: build-module
description: Second stage of building a solo-rpg ruleset module. Turns an approved staging SURVEY into a module plugin with page-cited rules files, validated table data, procedures, a manifest and generated skills, then audits it and produces a proof-reading checklist. Use after /solo-rpg-forge:ingest, or when resuming or repairing a partly built module.
argument-hint: "<module-id>"
disable-model-invocation: true
allowed-tools:
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(rpg-table *)
---

# Build a module

Module: $ARGUMENTS. Read `${CLAUDE_PLUGIN_ROOT}/references/module-spec.md` first. It defines
every file you'll produce. Staging lives at `<workshop>/staging/<module-id>/`
(`module_tool.py where` prints the paths).

The module will be used by a rules lawyer that may only cite what you write. **Omissions and
paraphrase errors become wrong rulings at the table**, so accuracy beats speed at every step.

## Resumability

Big books take more than one session. Keep `<staging>/<module-id>/BUILD-STATE.md` as a
checklist with one line per chapter, table group and procedure: `[ ]` todo, `[~]` in progress,
`[x]` done. Update it after every unit of work. On start, if it exists, read it, report
progress, and continue from the first unfinished item. Don't redo finished work unless asked.

## Steps

### 1. Scaffold
Needs an approved `SURVEY.md`. If it's missing, send the player to `/solo-rpg-forge:ingest`.
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/module_tool.py" scaffold <id> --title "<title>" --kind <kind>
```
Create BUILD-STATE.md from the survey's plan.

### 2. Rules files (parallel)
For each chapter whose plan is rules or lore, dispatch the **chapter-writer** agent. Batch
three or four at a time, and give each one a chapter. Each call passes: module id, module
dir, staging book dir, chapter title, PDF page range, page offset, target filename(s)
(`rules/NN-slug.md`), and the table ids planned for that chapter (so it writes
`→ table` pointers rather than copying tables). Each agent returns INDEX rows and glossary
terms. Merge those into `rules/INDEX.md` and `rules/GLOSSARY.md` yourself, sorted and
de-duplicated.

### 3. Tables (parallel)
Group the survey's tables by chapter. For each group, dispatch the **table-transcriber**
agent with: module id, module dir, staging book dir, the list of tables (title, printed
page, PDF page, dice), and the output folder `tables/<chapter-slug>/`. It reads the page
images, writes YAML, and runs `rpg-table validate` on its files until they pass.
Then run `rpg-table validate --module <id>` yourself. Chains (`then:`) across groups get
checked here. Fix or re-dispatch until you have zero errors. Warnings must be understood,
not ignored. Out-of-range rows are normal when the book applies modifiers.

### 4. Procedures
Write these yourself, because procedures cut across chapters and need the whole picture.
For each procedure in the survey, write `procedures/<id>.md` in the step-tag format
(module-spec §4). Source every step from the rules files you just wrote, using their `[p.N]`
markers, and check the book text where a step is unclear. Remember:
- Anything the book leaves to the GM becomes a **[CHOICE]** for the player.
- Name table and tracker ids exactly as they exist. Run `rpg-table list --module <id>` to check.

### 5. Manifest
Fill in `module.yaml`: dice (used + conventions with pages), records (fields from the character
sheet and stat-block definitions), trackers (min/max/default/scope/source), lists, and
procedures (id/title/when/file). Keep the ids consistent with procedures and tables.

### 6. Skills
Generate `skills/rules/SKILL.md` and one runner skill per player-facing procedure, using the
templates in module-spec §6. The rules skill's description decides whether Claude consults
the module, so pack it with the ruleset's distinctive terms.

### 7. Audit
Dispatch the **module-auditor** agent with the module id, module dir and staging dir. It
spot-checks tables and rules claims against the extracted pages and images, and writes
`AUDIT.md`. Fix every confirmed discrepancy. For systematic errors, such as a whole chapter
misreading two-column text, redo that unit.

### 8. Check and register
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/module_tool.py" check <id>
rpg-table verify-report --module <id>
```
Save the verify-report output to `plugins/<id>/VERIFY.md`. Update README.md with the sources,
the build date, known gaps and what the audit found.

### 9. Hand-off
Tell the player:
- What was built: counts of rules files, tables, procedures and skills.
- **Proof-reading**: VERIFY.md lists every table with its page. Once they've checked a table
  against the book, `rpg-table mark-verified <id>` records it. Unverified tables still work,
  and `rpg-table list` shows which are verified.
- **Install**: `/plugin marketplace update solo-rpg-workshop`, then `/plugin install <id>@solo-rpg-workshop`
  (or `/reload-plugins` if already installed). The module stays dormant until a vault enables it.
- **Next step**: `/solo-rpg-forge:vault-setup` in a campaign vault.

## Quality bar (check before hand-off)
- Every rules paragraph has `[p.N]`, and the INDEX lists every rules file.
- Every table in the survey exists and validates. Every `→ table` pointer resolves.
- Every procedure step is tagged and cited, and no step requires invented content.
- `module_tool.py check` reports OK.
