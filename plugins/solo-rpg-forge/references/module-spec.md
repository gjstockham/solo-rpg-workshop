# Module specification

A **module** is one ruleset — a game, a solo engine, a supplement, or a setting book — built
as a **project skill inside the player's own vault**. Modules contain data and instructions
only. All dice and table code lives in `solo-rpg-core`.

Because a module is a project skill, there is nothing to install or enable: it loads because
the vault is the project, and Claude Code watches `.claude/skills/` during a session. Only
two things need a restart — the first module built in a vault, because `.claude/skills/` has
to exist at launch to be watched, and any change under `.claude/agents/`.
Paths below are relative to the vault root, which
`module_tool.py where` prints. The forge never writes inside its own plugin folder (once
installed, that's Claude Code's plugin cache and is replaced on every update).

## Contents
1. Layout
2. Rules files
3. Tables
4. Procedures
5. module.yaml
6. Generated skills (templates)
7. Naming and size limits

## 1. Layout

```
<vault>/
  pdfs/<book>.pdf                        the player's own books
  .claude/skills/<module-id>/            THE MODULE (one skill)
    SKILL.md                             module knowledge, auto-triggered (section 6)
    module.yaml                          manifest (section 5)
    reference/
      README.md                          sources, build log, known gaps
      VERIFY.md                          human proof-reading checklist (rpg-table verify-report)
      AUDIT.md                           written by the module-auditor agent
      rules/INDEX.md                     file → topics → printed pages → keywords
      rules/GLOSSARY.md                  game terms, one line each, with [p.N]
      rules/NN-<slug>.md                 condensed rules by chapter or topic
      tables/<group>/<table-id>.yaml
      tables/VERIFIED.yaml               written by `rpg-table mark-verified`
      procedures/<procedure-id>.md
  .claude/skills/<module-id>-<procedure-id>/SKILL.md   one per player-facing procedure
  .solo-rpg/staging/<module-id>/         extraction, SURVEY.md, BUILD-STATE.md (build only)
```

Inside `SKILL.md`, refer to the module's own files through `${CLAUDE_SKILL_DIR}/reference/...`,
which resolves wherever the vault sits. A runner skill for a procedure lives in its own
directory (one skill per directory), so it reaches the module's data through
`${CLAUDE_PROJECT_DIR}/.claude/skills/<module-id>/reference/...`.

Each vault holds only the modules that campaign uses, so rules never leak between campaigns
and there is no enable/disable step. A module is moved to another vault by copying its skill
folder, but re-ingesting the PDF there is usually simpler and always current.

## 2. Rules files

Purpose: let the rules lawyer answer precisely without the PDF.

- **Page markers.** Put `[p.N]` (printed page) at the start of every paragraph or bullet.
  Page ranges use `[p.N-M]`.
- **Faithful condensation.** Keep every number, condition, exception, modifier and
  order-of-operations. Drop flavour text, repetition, examples of play (keep a one-line
  summary if an example clarifies an edge case) and art captions.
- **Verbatim where precision matters.** Keep exact wording for defined terms, trigger
  conditions, and short text that is itself mechanical (move or ability text, result
  definitions). Put it in quotation marks.
- **Structure.** `#` chapter title, `##` topic, `###` sub-rule. Sidebars and boxed rules
  become `> **Sidebar: title** [p.N]` blocks, so optional rules stay distinguishable.
- **Optional and variant rules** are labelled `**Optional**`.
- **Cross-references** use `(see 03-combat.md § Cover)`.
- **Tables are not copied into rules files.** Write `→ table \`<table-id>\`` where the table
  sits in the text, together with any usage conditions or modifiers from the surrounding prose.
- **Lore and setting chapters** go in `reference/rules/lore-*.md` using the same format but condensed
  harder. The INDEX marks them as lore, so the rules lawyer can deprioritise them.

`reference/rules/INDEX.md` row format:
`| 03-combat.md | initiative, attacks, damage, cover, morale | 40-58 | attack, hit, wound, armour, flee |`
Keywords should include synonyms a player might type, not only the book's terms.

## 3. Tables

Format: run `rpg-table schema`. Transcription rules:

- `id` is kebab-case and unique in the module. `title` is as printed. `source.page` is the printed page.
- `dice` is exactly what the book rolls. For d66-style tables, write `d66`. For percentile, write `1d100`.
- Row text is verbatim. Keep the book's capitalisation and punctuation. Put footnotes in
  table `notes`.
- A result that says "roll on table X" becomes `then: x-id`. "Roll twice" becomes `reroll: 2`.
  "Roll 1d6 and…" inside a result becomes `{{1d6}}` only when the number is meant to be
  rolled right away. Otherwise leave the text as it is.
- Tables indexed by two dice (row by one roll, column by another) become one table per
  column, or a `columns:` table when the column is chosen by situation rather than by a die.
  Say which in `notes`.
- Tables that are really lookup charts (no die, e.g. a cost list) are **not** tables.
  They go in the rules file as markdown.
- Group files by chapter: `reference/tables/<chapter-slug>/<id>.yaml`.

## 4. Procedures

A procedure is any ordered sequence the rules define: character creation, a scene or turn
loop, travel, an encounter, downtime, an end-of-session step, an oracle question, and so on.
File format:

```markdown
---
id: <procedure-id>
title: <as the book names it>
when: setup | session-start | scene | encounter | downtime | session-end | on-demand
source: "p.N-M"
inputs: [things the player must supply first]
records: [record types / trackers / lists this procedure reads or changes]
---
# <Title>

Short purpose line [p.N].

1. **[CHOICE]** Player decides <what> — options: A / B / C [p.N].
2. **[ROLL]** `rpg-roll 2d6 --label "<purpose>"`, applying <modifiers> [p.N].
3. **[TABLE]** `rpg-table roll <table-id> --mod <from step 2>` [p.N].
4. **[RULE]** If <condition>, then <consequence> [p.N].
5. **[RECORD]** Update <tracker/list/record field> by <rule> [p.N].
6. **[BRANCH]** On <result> go to step N; otherwise continue [p.N].
```

Step tags tell the runner what to do: CHOICE means pause for the player, ROLL and TABLE mean
call the script, RULE means apply it and cite, RECORD means edit the vault (reported in one
line), BRANCH means jump. Never write a step that requires Claude to invent content.
If the book says "the GM decides/describes", that step is a **[CHOICE]** for the player.

## 5. module.yaml

Created by `module_tool.py scaffold`. It lists `dice`, `records`, `trackers`, `lists` and
`procedures`. Every tracker, list and procedure carries a `source` page. `records[].fields`
lists the sheet fields the vault template will hold. Include computed fields only if the
book defines the formula, and record that formula in the field's `note`.

## 6. Generated skills

Both are project skills in the vault, so the directory name is the slash command. Keep the
directory names distinct from anything already in `.claude/skills/`.

### .claude/skills/<module-id>/SKILL.md (knowledge, auto-triggered)

The scaffold writes this with a TODO description; replace it. The description decides whether
Claude consults the module at all, so pack it with the ruleset's distinctive terms.

```markdown
---
name: <module-id>
description: <Ruleset title> rules reference — <6-12 key topics>. Use whenever play, a procedure or the player touches <ruleset title> mechanics, terms (<3-6 distinctive terms>) or tables, even if the question seems simple.
user-invocable: false
---
# <Ruleset title>

Module data: `${CLAUDE_SKILL_DIR}/reference/` — rules in `reference/rules/` (start at
`reference/rules/INDEX.md`), procedures in `reference/procedures/`, tables via
`rpg-table list --module <module-id>`.

Core loop in one paragraph (condensed, cited).
Dice conventions (cited).
Procedure list: id — when — one line.
For any non-trivial rules question, use /solo-rpg-core:rules (cite-or-abstain).
```

### .claude/skills/<module-id>-<procedure-id>/SKILL.md (player-invoked runner)

```markdown
---
name: <module-id>-<procedure-id>
description: Run the <procedure title> procedure from <ruleset title> step by step.
disable-model-invocation: true
argument-hint: "<inputs>"
allowed-tools:
  - Bash(rpg-roll *)
  - Bash(rpg-table *)
---
Run `${CLAUDE_PROJECT_DIR}/.claude/skills/<module-id>/reference/procedures/<procedure-id>.md`
for: $ARGUMENTS

Follow the steps in order. For [ROLL] and [TABLE] steps, use the scripts with --label and
--log (the current session note is in solo-rpg.yaml → current_session). At [CHOICE],
stop and wait for the player. Report [RECORD] edits in one line each. Cite pages. Do not
narrate or invent content. The play contract in the vault CLAUDE.md applies.
```

Only give a procedure its own skill if the player will start it directly. Sub-procedures that
are only reached from another procedure stay as files.

## 7. Naming and size limits

- Module id: `<short-title>` or `<short-title>-<edition>`, kebab-case. It is the skill name
  the player types, so keep it short.
- A rules file should stay under about 400 lines. Split big chapters by topic.
- A skill description should stay under 1,000 characters. Put distinctive terms in it so it
  triggers.
- Every rules paragraph, table, tracker, list and procedure step has a page reference.
  `module_tool.py check` enforces most of this.
