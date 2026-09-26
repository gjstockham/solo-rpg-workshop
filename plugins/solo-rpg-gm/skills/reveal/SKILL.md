---
name: reveal
description: After a solo-rpg-gm adventure is finished or abandoned, show the player everything that was hidden - every secret roll (with the sealed log's integrity check), what they never reached or met, every improvised fact, and the build audit. Only when the player explicitly asks.
argument-hint: "[adventure id]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
---

# Reveal an adventure

**This spoils the adventure.** Input: $ARGUMENTS (blank means the most recent adventure).

1. Check `rpg-gm adventure list`. If the adventure isn't finished or abandoned, say so and
   ask whether they really want to see it now; they could finish or abandon it first.
   Only with an explicit yes, use `--force`.
2. `rpg-gm reveal <id>` (with `--force` only as above). Present it:
   - the sealed log's check result, then the secret rolls, grouped sensibly (oracle
     questions next to their canon entries where the timestamps match);
   - what they never reached or met, with a line each from the adventure file if they
     want the detail;
   - the improvised canon;
   - the build audit's summary, and `AUDIT.md`'s path if they want to read it.
3. Offer to answer questions about the adventure now that it's over.
