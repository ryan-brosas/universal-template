---
title: paper-project-branding
summary: Use when branding a duplicated Paper component template, updating its theme through Figma-derived CSS variables, or explicitly setting up a Theme Control lane on the source template. Not for duplication, component reconstruction, or building project pages.
kind: playbook
---

# Paper Project Branding

Turn a duplicated component-template file into a project's branded starting point. The user duplicates the file separately. Authoring or discussing this skill is not authorization to run it.

For an explicit request to add or operate a **Theme Control lane**, read `references/theme-control.md`. Template setup preserves the current appearance and does not apply a project brand. Otherwise use the project-copy workflow below.

## Inputs and scope

Use the project repository, supplied brand guidance/assets, and the destination Paper copy. Discover existing information before asking questions. Confirm the destination file ID and that it is not the reusable source template before branding. If no duplicate exists yet, execution of branding waits. Only an explicit template-maintenance request authorizes control-lane setup or bounded binding repair in the source file; it does not authorize duplication, renaming, or applying a project brand there.

This skill owns project branding, not component repair or page composition. Consult `../paper-design/references/themes-and-tokens.md` for token mechanics and `../paper-component-consistency/README.md` for owner/usage relationships. Use `../pencil/references/component-repair.md` only when a translation defect blocks branding.

## Establish the brand mapping

1. Inspect project styles, token configuration, logos, font files, and brand guidelines. Prefer explicit user-approved guidance; surface conflicts between guidance and implemented styles rather than silently choosing. Do not invent missing brand decisions.
2. Read the duplicate's live tokens, aliases, modes, and representative component bindings. Revalidate IDs after duplication; copied IDs and structural linkage are not assumptions.
3. Map project choices onto existing roles: brand palette, text/surface roles, display/body typography, and explicitly requested radius or density settings. Keep success, warning, danger, focus, disabled, inverse, and selected-state semantics distinct. Preserve special typography such as monospace labels unless the brand explicitly replaces it.
4. Present one compact mapping for confirmation when choices are unresolved or change design direction. When the user supplied an unambiguous mapping, proceed without another approval ritual. Leave unspecified spacing, radii, and component geometry unchanged.

Reuse existing project/theme override tokens and alias chains. Trace their consumers before changing a shared value. Do not introduce a parallel token namespace or replace every matching color literal. A literal may represent an illustration, status, or intentional variant rather than the brand.

## Theme-first customization

A populated Theme panel is not a connected design system. Before branding, classify sampled properties as token-bound, aliased, detached literals, or intentional exceptions. Check across the affected pages, not only the currently visible family.

Use the chain **project values → existing semantic aliases → component property references**. Resolve aliases to their owner and update the smallest approved token set. Create a token only when a required reusable role is genuinely absent; do not reimport the system. CSS variables must exist in Paper's Theme and be referenced by editable properties, not merely written in a stylesheet or documentation.

For detached properties, establish semantic ownership before binding `var(--existing-token)`. Equal hex values do not establish the same role. Preserve the approved resolved appearance while reconnecting a property, then apply the project theme through tokens. Bind the categories actually customized: colors, font family/weight/size/line height/spacing, radii, and layout spacing where supported. Retain legitimate fixed geometry, artwork paints, and explicit local overrides.

Manual per-node updates are for restoring missing references or approved exceptions, not the branding mechanism. If the available tools cannot persist or resolve a required binding, report that limitation rather than replacing the theme with a literal-style batch.

## Apply a bounded preview

Capture affected token definitions, bindings, and asset properties for rollback. Establish a live baseline for this run, not an older project-wide audit.

Use representative button, field, navigation, and modal specimens where available, including contrasting states. File-level token changes may affect every bound consumer immediately: preview in an isolated supported scope when possible; otherwise disclose the file-wide effect and use a reversible batch. Do not describe a global token edit as a local canary.

Apply the mapped theme by editing its token definitions, then inspect propagation without separately restyling consumers. Repair proven missing bindings within the agreed branding scope; record ambiguous or unsupported properties as exceptions. Replace only identified project-brand slots with supplied logos/assets, preserving aspect ratio and layout. Keep instructional template content and unrelated artwork unless replacement is requested.

After a successful preview, batch matching exceptions within the approved property scope. Do not rebuild components or create project pages.

## Verify and resume safely

Check stored `var(--...)` references, resolved values, and fresh renders, not token counts alone. Demonstrate that one authorized token change reaches both direct and aliased consumers without additional per-node edits; include a non-color category when one is customized. Use an isolated fixture or the intended approved brand change, not arbitrary recoloring of a live file. Missing propagation means the theme is not fully connected. Inspect text fit, contrast for intended roles, icons, state distinctions, and representative owner/usage propagation. Theme propagation does not prove linked component structure or application accessibility.

After an ambiguous tool failure, inspect whether changes already applied. Failed screenshots leave visual verification pending; do not widen unverified changes or claim completion.

Record the destination ID, approved mapping, applied values, and unresolved exceptions in the project's existing design notes when useful for reruns. Before updating again, compare live values with the last applied state and preserve unrelated manual edits; ask about conflicts rather than overwriting them. No new registry or configuration framework is required.

Report what changed, what was verified, and what remains untouched or pending. Never claim the original template was customized: all authorized changes belong to the project copy.
