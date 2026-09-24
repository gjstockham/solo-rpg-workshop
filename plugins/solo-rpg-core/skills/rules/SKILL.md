---
name: rules
description: Answer a rules question from the installed ruleset modules with page citations, via the rules-lawyer subagent. Use when the player asks how a rule works, what modifier applies, what happens on a result, or whether something is allowed, or when a procedure step needs a rules check.
argument-hint: "[rules question]"
context: fork
agent: rules-lawyer
background: false
---

Answer this rules question for the current campaign: $ARGUMENTS

Work from the campaign directory. Active modules are listed in `solo-rpg.yaml`; the house-rules
note path is in the vault's CLAUDE.md.
