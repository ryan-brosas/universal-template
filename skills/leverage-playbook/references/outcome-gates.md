# Outcome Gates — steer outcomes, not behavior

Source: Tom, 8/11/26 (verbatim block: `~/.agents/essentials/discord-material/raw/block-002-e06b4b3d911d.md`).

## The principle

> The idea is not to steer behavior but to steer outcomes. Everything should be technically verifiable, even code taste.

Rules you'd be tempted to write in AGENTS.md as prose usually translate 1:1 into a CI check or a gate. Writing them as a check lets the agent iterate fast AND gives it a self-correcting loop; a prose rule is an unenforced belief.

## The pipeline

1. Identify the principle — e.g. "Don't preserve backward compatibility", "no speculative abstraction", "grow in layers, working end to end first", "prefer established libs", "study established products before inventing".
2. Ask: is this mechanically verifiable? If yes → make it a gate/check and drop the prose.
3. If it's genuinely a taste/preference with exceptions, keep at most a small exception line, never a sweeping rule (sweeping rules affect post-training / get dropped).

## The loop

- Do the checks at the end, not the beginning — iterate fast, then let the agent loop through the tests.
- If you create PRs: `Create a PR and gh watch the CI and resolve any issues.` — a conclusive loop.

## Antipatterns from the source

- Overly restricted, "scope-disciplined" AGENTS.md can be the *cause* of a stalled project — it restricts the agent before it can do anything. Tone: checkable outcomes get tightened; prose rules get cut.
- "Choose the simplest implementation…" style lines on their own "sound good on paper" but drift the session — because there's no verifiable trigger. That is why they get converted to gates instead of kept as prose.