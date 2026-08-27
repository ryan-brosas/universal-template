# Mechanical Gate Ladder — quality packs and unbypassable gates

Source: scarywood75, 7/19/26 (verbatim block: `~/.agents/essentials/discord-material/raw/block-004-4267-…md`).

## Anything mechanical → a test or gate

Anything deterministic: exposed functions not used elsewhere, non-existent consts, unused imports, duplicate detection via semantic comparison (how far is function X from function Y; near-identical ⇒ duplicate). Removing responsibility from the LLM, which "tends to forget and makes mistakes."

## Quality packs

- A **quality pack** = a set of gates. One pack is universal across all languages (structure, hygiene); others are language-specific (e.g. TS, Python).
- After adding a gate, the harness runs it in CI; the agent's session never "passes" without the pack green.

## Gates vs prompts (the core contrast)

> Prompting for something that can be mechanically enforced is useless.

Example from the source: "I want my agents to use the web as much as possible, so I created a gate that does not allow them to go further until they have called and used the researcher agent — because telling my agent to research by prompting does not consistently work, while the gate cannot be bypassed."

## Applying

- When a project has a rule that is *behaved* ("use AI to research", "lint style") turn that rule into a gate/check the first time it is violated, not a reminder.
- The gate runs at the end of iterate loop: fast iteration while green; a red gate halts (never bypass, never waive silently).
