---
title: figma-web-design
summary: "Use when setting up or running a Figma web-design workflow from existing libraries or an approved blueprint: inspect assets, preserve components and variable bindings, and verify the deliverable's source mapping."
kind: playbook
---

# Figma web-design workflow

Start with the assets the project already owns, not a new token system. A
blueprint is useful only when it exists, is suitable, and can be reused under its
access and license terms.

## Start a project

1. **Inspect the sources.** Search Assets, enabled libraries, other pages and
   available templates for components, variants, styles and variable collections.
   An empty published-component search does not establish that no template exists,
   and neither does an empty library-variable list. `figma_get_library_variables`
   reports variable collections only, so an empty result can coexist with several
   enabled libraries. Reach a library's contents by key via the
   [MCP library probe](../pencil/references/mcp.md#published-libraries).
2. **Choose the approved source.** Work in a permitted copy or destination file;
   change source masters only when the user's scope includes them. If access or
   a suitable asset is missing, report
   the gap and ask instead of fabricating a substitute.
3. **Preserve bindings.** Use linked instances and exposed properties. Import
   source variables with their modes and aliases. If linking is unavailable,
   copy the source variables faithfully and record the mapping; do not flatten
   bindings or invent replacement values.
4. **Make only required adjustments.** Change content, layout and sizing within
   the task. Palette, typography or system-wide changes need explicit scope;
   duplication alone does not authorize retheming or deleting unused variables.
5. **Reuse the source structure.** Use its page skeleton and layout starter when
   suitable: [page structure](references/page-structure.md) and
   [layout grids](references/layout-grids.md). Layout-only containers are allowed,
   not a substitute for library UI.

## Repair an existing system

First classify the element’s job. Editorial reading links, browse controls and
conversion actions can need different canonical treatments. Compare each with
the approved example for the same role. A request for uniform buttons does not
authorize turning editorial headings into buttons or giving every action the
strongest accent.

For inconsistent linked controls, use the
[configured-instance audit](references/components.md#audit-configured-instances).
Start with the user's approved example and inspect its selected variant and
properties, then verify the affected source and actual consumers at each breakpoint.
Component membership and token coverage alone do not establish visual consistency.

For an authorized palette correction, read current variables before older docs.
Review which section and action roles deserve the accent, including interaction
states; a correctly bound token can still express the wrong visual hierarchy.
Preserve established logo assets and semantic aliases while changing only the
approved roles or values.

## When new system work is authorized

Inspect existing access and font availability before onboarding or installation.
Account, billing, security, public-profile and installation actions remain
user-controlled. Check licenses before adding fonts or assets.

If the user explicitly requests a new blueprint or missing components, build only
what the task needs: variables, bound styles, then components. The references
contain course examples, not default project values:
[design system](references/design-system.md),
[components](references/components.md), and
[elements and styles](references/elements-and-styles.md).

## Working rules

- Preserve the source naming, modes, aliases and component relationships.
- Prefer exposed variants and properties over overrides that detach bindings.
- Inspect intended alignment; odd or fractional measurements alone are not bugs.
- Preserve editable originals. Outline or flatten only an authorized export copy
  when the target format requires it, never a linked asset in the deliverable.
- Propose removal of unused material only after checking dependencies and obtaining
  approval for user or shared content.
- On a canvas the user also works in, agree the direction before creating material,
  then add one section at a time and check in. Building a token, style and component
  layer ahead of an agreed plan produces rework the user has to review, not progress.

## Boundaries

Figma-to-Paper transfer stays with [pencil](../pencil/README.md); interactive
prototypes with [prototype](../prototype/README.md); accessibility conformance
with [wcag-accessibility-practices](../wcag-accessibility-practices/README.md).

## Verification

Inspect the finished deliverable, not a separate asset demo. Confirm source
component identities, linked instances, variable bindings, modes and aliases;
record any approved copied-variable mapping. Verify fonts, required viewports,
alignment and rendered output. A screenshot proves appearance, not provenance.
A capture can also reach the agent as image data it cannot visually inspect; state
that limit instead of describing a render you did not see, verify geometry, bindings
and provenance through the plugin API, and ask the user to confirm the visible result.
When a visual defect is reported, ask for a pasted screenshot early rather than
re-measuring: a user-pasted image is readable, while geometry probes answer a different
question and cannot see a clip inside a linked library component.

See [source notes](references/source-notes.md) for attribution and limitations.
