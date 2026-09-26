---
name: challenge
description: Review a GM ruling the player disputes in a solo-rpg-gm (GM-style) campaign, using the rules lawyer's cited reading of the rules module and house rules, and correct the ruling if the rules say otherwise. Use when the player challenges or questions a ruling.
argument-hint: "[which ruling, or blank for the most recent]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
  - Bash(rpg-roll *)
  - Bash(rpg-table *)
---

# Challenge a ruling

The ruling in question: $ARGUMENTS (blank means the most recent one).

1. **State the ruling** as you made it: the situation, the rule you applied, and its
   effect, in mechanical terms. Don't reveal hidden adventure facts to the player here.
2. **Ask the rules lawyer** (`/solo-rpg-core:rules`, which uses the vault's
   `rules-lawyer` agent) the underlying rules question. Give it the mechanics it needs,
   including hidden numbers if the question turns on them; its answer isn't shown to the
   player in full, and yours below shouldn't repeat those numbers.
3. **Act on the answer**:
   - **The rules support the ruling**: say so with the citation, and play on.
   - **The rules say otherwise**: correct it. Undo or adjust what followed with `rpg-gm`
     (hit points, state, clocks) and the player's notes, re-roll only if the corrected
     rule calls for a roll, and log the correction in the session note.
   - **The rules are silent or ambiguous**: lay out the readings with citations. The player
     decides. Record the decision in the house-rules note, dated, with the question it
     settles.
4. Return to play where it stopped.
