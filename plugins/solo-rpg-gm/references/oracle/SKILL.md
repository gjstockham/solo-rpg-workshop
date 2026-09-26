---
name: gm-oracle
description: Built-in oracle for solo-rpg-gm campaigns, where Claude runs a published adventure as GM. Yes/no questions by likelihood (very-unlikely to very-likely) with "and" and "but" results, and an attitude table. Use when running the adventure and a significant question is answered neither by the adventure nor by the rules module (improvisation ladder step 4), before deciding anything important yourself.
user-invocable: false
---
# GM oracle

Tables: `rpg-table list --module gm-oracle`. Rules for using them:
`${CLAUDE_SKILL_DIR}/reference/rules/01-oracle.md`.

In short: frame a yes/no question, choose the likelihood column from what's established,
then roll it secretly and follow the answer:

```
rpg-table roll gm-oracle/yes-no --column <likely|even|...> --secret --label "gm check" --log "<session note>"
rpg-gm canon "<the question, the likelihood, the answer and what you made of it>" --basis "oracle"
```

(`rpg-gm canon` arrives with the play tools; until then, note the result in the session log.)
