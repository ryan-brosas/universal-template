---
name: pencil
description: "Use when copying a Figma frame, component set, variables, or visual reference into Paper with literal source fidelity."
invocation: entry
---

# Pencil

For exact transfer, Figma is the spec. For intentional project adaptation, preserve
source evidence but use approved project theme and component owners; record
meaningful differences. Never silently blend systems. **No fresh visual comparison
means no pixel-perfect claim.**

Use for Figma/reference transfer into Paper, not application implementation or
website copying. For Paper-native composition and maintenance, load
`../paper-component-consistency/SKILL.md`. For Paper platform mechanics, themes/CSS
variables, clipboard import, and new capabilities, load `../paper-design/SKILL.md`.
Direct Figma paste is a candidate editable fast path; inspect translation losses
and repair detached bindings before treating it as a transferred system.

## Working approach

Derive scope, measurements, and organization from the active source, not reference
examples. Choose efficient tools and ordering; preserve actual dependencies such
as creating referenced tokens and confirming the destination before mutation.
For captured images without source nodes, use the captured-reference branch in
`references/figma-fidelity.md` instead of Figma node/variable calls. Editable
construction, destination checks, and fresh visual comparison still apply.

- **Establish context.** Confirm connected Figma and Paper file/page identities.
  Run small render canaries. Verify required fonts are available and actually
  render; a retained family name is insufficient. Missing fonts block pixel-perfect
  claims; use fallbacks only with explicit acceptance.
- **Understand the system.** Inspect targeted source nodes and renders: components,
  instances, overrides, styles, variable aliases, inherited modes, content, and
  layout behavior. Truncated dumps are incomplete evidence; split reads or inspect
  saved complete output (`references/mcp.md`).
- **Carry the theme.** Compare source decisions with existing Paper bindings and
  project code tokens when present. Resolve ownership, reuse appropriate tokens,
  and bind actual properties, not matching literals. Probe current mode/scope
  capabilities; distinguish working switches from previews (`references/tokens.md`).
- **Reuse built work.** Inspect relevant Paper specimens and page patterns before
  rebuilding. Prefer established owners; a copied screen is usage evidence, not
  automatically canonical. Reuse matching anatomy, nested components, slots,
  variants, and assets through verified native linkage or explicit copy projections
  (`../paper-component-consistency/SKILL.md`). Build only missing/divergent parts.
- **Preserve fidelity.** For exact transfer, retain source page/artboard organization,
  Overview sheets within scope, coordinates, text, and variant matrices
  (`references/organization.md`). Match fills, strokes, effects, layout, and type
  metrics. Export actual IMAGE fills and SVG vectors, not convenient substitutes.
  Component image fills are valid; whole-component/page screenshots are reference
  evidence, never editable deliverables.
- **Mutate safely.** Open the intended page and pass explicit file identity on Paper
  mutations. Capture recovery proportional to risk; snapshot JSX before destructive
  edits. After ambiguous failure, inspect before retrying: inner mutations may have
  succeeded (`references/completion-contract.md`).
- **Verify.** Audit names, counts, bounds, content, assets, and bindings. Inspect
  fresh source/Paper renders and a diff per block (`references/figma-fidelity.md`).
  Structural agreement is not visual proof. Pending rendering means
  **structurally verified, visual pending**, not permission to announce the next
  page. Customized compositions need their own content/variant checks, not a false
  claim of identical source pixels.

## Completion

Distinguish **built**, **structurally verified**, **visually verified**, and
**pixel-perfect**. Only passing structural, visual, theme, asset, and font gates
permits an unqualified exact-transfer completion claim.

For exact transfers, run `scripts/verify-fidelity-manifest.py <manifest.json>` and
inspect its saved source, Paper, and diff artifacts before advancing. Release
working indicators. Report exact affected file/page/artboard IDs, reused owners,
intentional differences, constraints, and actual verification, not assumed linkage.

## Focused references

- `references/layout.md`: source grid translation.
- `references/component-repair.md`: pasted-family repair patterns, canaries, and trustworthy verification baselines.
- `references/official.md`: platform notes; current capabilities outrank snapshots.
- `references/behavior-tests.md`: fidelity and reuse regression scenarios.
