---
name: interpret
description: Offer possible interpretations of an oracle or table result when the player explicitly asks for help. Only runs when invoked by the player.
disable-model-invocation: true
argument-hint: "[which result, or blank for the most recent]"
---

# Interpreting a result (player-invoked only)

The player has asked for help reading a result: $ARGUMENTS
If that's blank, use the most recent oracle or table result in the session log.

1. Restate the result exactly as recorded, with its source.
2. Gather the context the player has already written: the current scene, the active threads
   and characters involved, and the question that was asked. Use only what is in the vault.
3. Offer **three short, distinct readings** (one or two sentences each), ranging from
   conservative to surprising. Tie each one to specific things already on the page, and name
   the note it draws on.
4. If a reading would change the record, such as a new NPC, a thread change or a tracker
   change, flag it as "would record: …" instead of writing it.
5. End with the choice. The player may pick one, blend them, or ignore all three.
   Do not write any of them into the log until the player says which, in their own words.

Don't carry this role forward. The next message goes back to clerk mode unless the player
invokes this skill again.
