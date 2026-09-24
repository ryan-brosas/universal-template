---
title: visual-asset-iteration
summary: "Use when iterating logos, illustrations or lettering from approved artwork, or delivering visual revisions to a canvas such as FLORA; preserve editable sources and verify resumable checkpoints. Not a UI-flow or component-template branding procedure."
kind: playbook
---

# Keep visual revisions editable and resumable

A rendered preview, an editable master, and a visible canvas checkpoint are
separate deliverables. Preserve the material needed for the next revision,
not just the image shown in chat.

## Establish the revision boundary

Identify the approved baseline, requested change, exact wording where relevant,
and protected artwork. Keep draft status separate from user approval. Read the
actual reference and existing assets before choosing a construction method.

When an example suggests a new direction, or a technically sound draft misses
its intent, [interpret the reference](references/reference-intent.md) before choosing
a font, redraw or construction technique.

Use controlled edits when geometry must remain fixed; a generative redraw is not
evidence of preservation. Complete letterforms or shapes from a supplied reference
can be reused as linked vector definitions or traced components. Inspect them for
clipped boundaries, cursor marks and other capture artifacts. Keep a source mapping;
do not silently substitute a stock font or invent missing artwork.

For variations of accepted shapes, compare a small set of named changes such as
width, height, spacing or tilt using shared source geometry. Label what differs.
After selection, lock that baseline and edit only the requested subset; a
punctuation revision need not reopen the letter design. Keep illustration,
lettering and combined lockups separate when requested. This does not rule out
an authorized redraw; it distinguishes exploration from preservation.

## Keep the next edit possible

Start in a persistent project or user-selected working folder. Preserve the supplied
reference, editable master, and any generator inputs needed to rebuild it before
transforming them. Temporary storage is fine for reproducible scratch work, not the
only copy of a draft, reference or recipe. A flattened canvas image does not replace
an SVG, native editable document, or rebuild source.

Work on a new revision without overwriting the approved baseline. For protected
regions, compare vector structure or pixels at the same scale and coordinates;
inspect the changed region visually as well. Exact spelling and shape continuity
need their own checks. A hash proves identity of compared bytes, not design quality.

## Checkpoint on the requested surface

When the canvas is the agreed collaboration surface, finish the revision's
checkpoint before advancing to the next revision or calling it delivered:

1. Save the editable source and preview durably. Keep source references or separated
   components when the next edit needs them; a one-off local export need not upload.
2. Discover the platform's current asset and canvas contracts. Confirm workspace,
   destination, ownership and input capabilities. Resolve targets from fresh readback
   using stable identity plus label/content; short IDs can be recycled after deletion.
   Upload permission is not implied by mere tool access.
3. Finalize the upload and retain its asset ID/URL before placing it. Reuse a completed
   asset if only canvas placement failed. Uploaded bytes alone do not prove a node
   exists. In node-generation canvases, edges are executable inputs, not provenance
   annotations: inspect the target's ports before connecting.
4. Read back the created nodes and inspect the served preview. Compare framing,
   dimensions and protected artwork; allow documented delivery compression rather
   than demanding byte equality from an optimized preview. Verify expected edits and
   protected content separately from unrelated state such as canvas positions.
   Investigate unexpected differences without assuming who caused them or reverting
   others' work. Include positions when layout is part of the request. Report what
   was preserved and what remains uncertain, and distinguish draft from approved.

FLORA imports created with `content_url` have been observed as source-only image
nodes; generation nodes are a different case. Use notes for source relationships
when imported nodes have no input ports. Do not create or run a generation merely
to make a provenance edge valid. Recheck live capabilities rather than assuming
all nodes sharing the `image` type have identical roles.

After a failed batch, inspect actual local and remote effects before retrying only
unfinished work. If publication is blocked, name the durable local checkpoint and
the missing external step; do not claim the canvas is updated. Record master
locations and next-edit constraints in existing project/canvas notes when useful,
not a parallel registry or a transcript archive.

## Missing working files

A missing temporary path does not establish that the source is unrecoverable or
explain who removed it. Before asking for another upload, check surviving masters,
the requested workspace and authorized retained attachments. For host/session
recovery use [artifact recovery](../fabric-native-execution/references/artifact-recovery.md).
Keep the recovered sources durable before resuming.
