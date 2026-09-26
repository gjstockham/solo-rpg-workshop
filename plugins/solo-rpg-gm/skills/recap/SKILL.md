---
name: recap
description: Recap recent sessions of a solo-rpg-gm (GM-style) campaign from the player's session notes. Use when the player asks what happened last time or in the last few sessions.
argument-hint: "[number of sessions, default 1]"
disable-model-invocation: true
---

# Recap

Summarise the last $ARGUMENTS sessions (default 1) from the session notes in
`solo-rpg.yaml` → `paths.sessions`, oldest first.

- Use only what the notes record, plus `Known/` for names the party has learned. Never
  read `.solo-rpg/`: a recap is the party's memory, not the GM's.
- A few lines per session: where they went, what they found and learned, who they met,
  fights and their cost, and how it ended. Quote the notes' wording where it helps.
- End with the loose ends from the latest session's `## End` section.
