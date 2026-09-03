---
name: pixel-perfect
description: "Use when a design copy must match its source pixel-perfectly — Paper↔Figma fidelity checks, fixing 'it looks off' or 'not accurate' feedback, verifying fills, radii, shadows, type metrics, or fonts against the design source, or before calling a design match done."
---

# Pixel-Perfect Design Fidelity

## Core Principle
The reference render is the spec; node data is the evidence. Never judge fidelity from memory of the source — render the full reference page, then verify every claim against computed styles on both sides.

## When to Use / NOT
- **Use when:** a copied design "looks strange" or "doesn't match", the user gives vague accuracy feedback ("not detailed", "not the same"), or fidelity gates done-ness.
- **NOT when:** designing new content with no source, or implementing app code from a design (frontend skills own that).

## Workflow
1. **Render the whole reference page first** — a full-page screenshot of the source, saved to disk beside the work. Per-node data alone hides the composition.
2. **Confirm the target before destructive edits.** HARD-GATE: state exactly which nodes a match removes and get the reference confirmed; keep JSX/HTML snapshots of anything removed so it can be restored.
3. **Diff structure** — enumerate top-level items on both sides (ids, names, bounds). Blocks existing on one side only are the "disconnected stuff"; that list is the fix scope, not a mandate to empty the page.
4. **Resolve, then write** — every fill, radius, shadow, line-height, letter-spacing, and gap comes from computed styles on a source node, never from plausible defaults. Unknown token values get read from a surviving node that uses them.
5. **Fonts** — probe availability (Google Fonts CSS API + `fc-list`) before writing any family. Keep the closest installed stand-in and say so plainly; never decorate a fallback as if it were the design.
6. **Verify per block** — screenshot each written/restored block; whole-artboard renders time out. Compare against the matching reference crop; fix before moving on.
7. **Stop** when the final render matches the reference, or the user redirects.

## Red Flags
- Deleting chunks before the reference is confirmed and the removal list stated.
- Judging fidelity from a node dump instead of a render.
- Guessing a font family or a token value; inventing a showcase the source does not show.
- Retrying a dead MCP screenshot session more than once — restart it.
- Reading "not detailed" as "delete everything" — sparseness is a diff result, not an instruction.

## Verification
- Same item count, positions, and sizes (±0) on both sides; fills, radii, shadows, and type metrics equal per node.
- Final target render compared against the full-page reference render; both saved beside the work.

## References
- `references/verification-recipes.md` — dump scanning under truncation, font probes, per-node style diffs, stale-session recovery.
