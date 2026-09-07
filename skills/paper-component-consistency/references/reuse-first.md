# Reuse-first Paper composition

## Pick the cheapest existing source

Check the project's component index and usage notes if they exist. Search by a
semantic key and variant, not a remembered node ID. If no index exists, inspect
only relevant pages and specimens. Prefer a complete menu or header over rebuilding
it from primitives. Prefer an existing exact avatar/icon/button variant over
recreating its appearance. A superficially similar component is not an exact match.

Keep project IDs, content, source evidence, recipes, and consumer mappings in the
project. The shared skill owns the procedure, not one team's catalog. Add an index
only when repeated discovery or shared slot boundaries justify maintaining it.

## Efficient execution

1. Confirm file and destination. Validate the source's name, parent, variant,
   dimensions, and needed descendants against live data. Resolve ambiguous or
   conflicting owners before mutations.
2. Inspect source anatomy once. Declare text/image/component slots, compatible
   variants, protected styles, and content-fit behavior. Capture source evidence
   and a recovery snapshot proportional to the proposed change.
3. Use verified native instances/overrides where available. For copy projections,
   duplicate the source and save each returned source/new-root pair and descendant
   mapping immediately. Never treat duplication as native linked-instance creation.
4. Resolve all dependent targets through those mappings before applying a batch.
   Reject missing mappings, shared targets between copies, or targets that point
   back to originals. Map a nested component's destination before cloning it.
5. Batch compatible text/style changes on copies. Keep custom content separate
   from shared rules. For later synchronization, apply an explicit property
   allowlist and preserve consumer overrides; conflicts need review.
6. Verify the copies and source preservation. Save readiness separately from
   lineage, and retain actual receipts for recovery. An ambiguous mutation failure
   requires inspection before any retry; do not replay the whole recipe blindly.

Use a project's tested recipe helper when available. A helper may emit tool
arguments without owning transport. Read its usage notes and capability-probe
actual operations before applying arguments. Do not invent a second MCP connection.

## Slot fitting is part of the contract

A text substitution can succeed while making the layout unusable. Source text
nodes often have fixed widths sized for their original labels. A longer name can
wrap into the email line; a longer search hint can escape the input.

For a declared single-line slot, fit the text to its existing available parent,
not to the entire artboard. Choose wrapping, ellipsis, or expansion according to
that component's intended behavior. Preserve row height, icon lanes, badge sizing,
and typography unless the variant explicitly changes them. Do not stretch every
text node indiscriminately: centered initials and number badges need their own
rules. Compare a short value and a long value in fresh renders.

For literal Figma replication, keep the source contract: do not introduce a new
content-fitting policy merely to conceal a mismatch. `pencil` owns that fidelity
workflow; composition is an intentional customization of a specimen.

## Readiness and rendering

Distinguish source fidelity from successful composition. A structurally usable
source can enter a labeled experimental pilot; it cannot enter a pixel-perfect
catalog on the strength of a successful clone. A pending source stays pending
until its own fresh source/target comparison passes. Customized text and avatar
variants are intentional differences, not pixel-perfect copies of the old content.

A real image export can substitute for a screenshot tool when the screenshot
transport fails. Confirm the exact file/page and inspect the returned file. An
empty result or a missing DOM node is not a clean image. A desktop view at low
zoom can diagnose viewport state but does not prove pixel fidelity. If rendering
remains unavailable, preserve the work and report visual verification pending.

## Evidence to keep

For a reusable project library, keep only what avoids repeated work: semantic
keys, source locators and identity checks, declared slots/variants, source evidence,
recipes, actual clone receipts, intentional overrides, and current verification
status. Readiness is not inherited across edits, source changes, or token changes.
