---
name: end
description: End a GM-style play session in a solo-rpg-gm vault - brings the player's notes up to date, closes the session note and checks the hidden state and sealed log. Use when the player wants to stop, pause or wrap up the session.
argument-hint: "[anything to note about stopping]"
disable-model-invocation: true
allowed-tools:
  - Bash(rpg-gm *)
  - Bash(rpg-sealed verify)
---

# End the session

Follow the GM play contract in the vault's `CLAUDE.md`: nothing hidden goes into
player-visible notes. Input: $ARGUMENTS.

1. **Player-facing notes.** List the updates you'd make, one line each, then apply them
   once the player agrees:
   - character notes: hit points, resources, conditions, gear, experience or advancement
     the rules module awards at session end (cite it), deaths;
   - `Known/`: new entries for what the party learned this session; mark entries
     `outdated` if play proved them wrong;
   - `Campaign.md`: campaign-scoped trackers from the rules module, and the adventure's
     status if it changed.
2. **Hidden state.** Make sure everything that changed is recorded with `rpg-gm` (position,
   visited elements, creatures, fired events, clocks, time, taken treasure) and every
   improvised fact that might matter again is in canon. `rpg-gm state show` if unsure.
3. **Close the session note**: a `## End` heading with where the party is (as they'd put
   it), loose ends as the party knows them, and anything from $ARGUMENTS. Terse, one line
   each.
4. **Check** `rpg-sealed verify` and report the one-line result.
5. If the adventure reached one of its endings, ask the player whether to mark it
   finished (`rpg-gm adventure finish <id>`), and mention `/solo-rpg-gm:reveal` for
   afterwards.

Finish with one line: the session note's name and where the party stands.
