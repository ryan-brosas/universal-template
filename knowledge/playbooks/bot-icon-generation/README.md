---
title: bot-icon-generation
summary: "Use when converting a supplied person or character image into a minimal 2D bot avatar with black capsule eyes, including requests for a Grok bot icon; preserves target identity and a tilted close-up composition. Not a general image-generation style."
kind: playbook
---

# Convert a subject into a minimal bot icon

Here, “Grok bot icon” names the visual specification, not a required model or
provider. Use this style when requested; do not impose it on unrelated artwork.

## Decide whether to generate

- A creation/conversion request, or one attached target with no separate question,
  calls for one completed icon.
- Inspect the actual target image before describing or transforming it. If it is
  missing, inaccessible, or unverifiable, request an attachment; do not invent a
  subject. If several people or characters are present without a selected target,
  ask whom to convert.
- For prompt editing, skill authoring, rule explanations, result analysis, or usage
  questions, answer in writing without generating. Provide written production
  specifications only when requested.

## Generate and inspect

1. Read [the complete visual specification](references/visual-spec.md) before
   generation or revision. Extract base colors and at most three identifying
   features from the target only. A separate style reference supplies no identity.
2. Discover an available image-generation/editing tool and inspect its live input
   contract. Supply the inspected target as image input and the full specification;
   identify target versus style-only inputs explicitly. Do not silently substitute
   a text-only recreation for reference-based conversion.
3. Generate one square icon. Inspect the actual output at full size and thumbnail
   scale against every specification section, applying its collision priority.
   Correct visible violations before delivery; a successful tool call alone does
   not establish visual compliance.
4. On later revisions, change only the requested parts. Preserve character
   identity and these style rules unless the user explicitly changes them; use
   the prior result and original target as references where supported.

## Deliver

On success, return only the single completed, inspected icon: no preamble,
explanation, caption, or production specification. Do not deliver a prompt instead
of an image. If generation, inspection, or image delivery is unavailable or fails,
briefly report the blocker rather than implying completion. Clarification and
failure messages are exceptions to image-only delivery.
