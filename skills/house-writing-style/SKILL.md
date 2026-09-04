---
name: house-writing-style
description: "Use when rewriting, polishing, or auditing natural-language prose in the house style: agent output, docs, release notes, PR and issue text, or when a style choice needs explanation."
invocation: entry
---

# House Writing Style

## Core Principle

Use plain technical English for prose the agent authors. Style is a judgment
surface, not a publication regex. Clarity, fidelity, audience, and the artifact's
purpose outrank any isolated preference.

## When to Use / NOT

- **Use when:** drafting or reviewing public docs, release notes, PR text, issue
  text, or other important prose.
- **NOT when:** the user requests another style, or the material is protected.

## Protected content

Keep source code, commands, identifiers, paths, URLs, hashes, structured data,
logs, compiler errors, exact quotations, citations, and fidelity-sensitive
upstream text byte-exact.

## Review guidance

Prefer direct sentences, concrete verbs, necessary terminology, and varied but
natural cadence. Remove filler, throat-clearing, performed enthusiasm,
unnecessary hedging, and decorative conclusions when they obscure the point.
Use parallel structure for lists and protocols. Keep technical contrasts when
they prevent ambiguity. An em dash, long sentence, nominalization, or domain
term is acceptable when it is the clearest faithful choice.

## Workflow

1. Identify the audience, purpose, and protected spans.
2. Read the whole passage for meaning before editing individual words.
3. Improve clarity, precision, structure, cadence, tone, and economy with one
   bounded pass.
4. Re-read against the source and restore any lost qualification or technical
   distinction.

## Red Flags

- Rewriting protected content to satisfy taste.
- Treating a vocabulary list or sentence length as proof of quality.
- Flattening all prose into uniform short sentences.
- Claiming formal ASD-STE100 compliance.

## Verification

The model reads the final prose in context, checks protected content for exact
fidelity, and explains any consequential style tradeoff. Style preferences do
not block publication mechanically.

## References

- `references/rules.md`, detailed review considerations.
- `references/examples.md`, contextual examples.
- `references/exceptions.md`, protected and justified exceptions.
