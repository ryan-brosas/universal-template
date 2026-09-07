# Carry a functional theme into Paper

## Resolve ownership and identity

Inspect the relevant Figma bindings, styles, aliases, and inherited collection
modes alongside existing Paper tokens and the project's code token source, if any.
For literal transfer, preserve source decisions. For project adaptation, reconcile
with approved project owners and identify meaningful differences. Do not silently
combine palettes. A copied screen is a usage example, not automatically authority.

Map by source identity, semantic role, and usage, not equal hex or pixel values.
Brand and success can share a value without sharing a decision. Preserve coherent
names and useful aliases; reuse an appropriate existing token before adding one.
Naming conversion must handle collisions without merging distinct variables.
Primitive, semantic, and component layers are options, not required scaffolding.
Keep actual values, mappings, source links, and product decisions in the project.

## Bind properties, not swatches

Carry the dependency closure needed by the selected work, not the entire library.
Read bounded token groups or inspect the saved complete response when an inventory
is truncated. Create missing alias targets before their consumers where required.
Use live schemas for supported types and operations; check per-entry results.

Bind reusable colors, typography, spacing, radii, and layout widths to the shared
theme where supported, usually through `var(--token)`. A resolved value equal to a
token is not a binding. After paste, import, or duplication, inspect actual stored
references as well as rendered values; repair missing bindings deliberately.
Keep unsupported properties with the smallest existing component/style owner.
One-off geometry does not need a new token, and an unbound source value does not
automatically justify one. Distinguish observed bindings from inferred proposals.

Preserve units and relationships. Interpret percentage line height against font
size (for example, 150% of 16px is 24px), and percentage letter spacing as a ratio
of font size, not pixels. Preserve opacity and alias semantics. Confirm whether
conversion should remain relative when type size changes. Do not substitute fonts
silently or treat a retained family name as proof that its font rendered.

## Modes and scope

Inspect the selected node's resolved and inherited modes, not just a collection's
first value. Brand, light/dark, density, typography, and width may be independent
axes. Carry only relevant choices without flattening them or generating their full
Cartesian product.

Probe the installed Paper version's native themes, modes, and scoped overrides
when needed. Use supported features; old documentation is not a capability veto.
Where mapping is partial, combine native behavior with the smallest honest
fallback: explicitly named previews or scoped values. Report which alternatives
actually switch and which are representations only. Different preview values must
not accidentally share one mutable alias target.

Treat same-file and cross-file reuse separately. Confirm whether dependencies are
linked or copied and which source owns updates. Copied tokens do not establish
cross-file synchronization. Shared product themes need explicit consuming-project
override boundaries, not global changes that restyle unrelated products.

## Verify propagation safely

Identify relevant consumers, including transitive aliases and other pages, before
changing a shared value. Tool searches may be page-scoped: an empty local result
is not proof of no consumers. Distinguish a local variant from a system decision.

Use an approved change or isolated fixture to observe bound properties changing
across consumers; inspect fresh renders as well as references. Separately verify
how a component's anatomy/layout change reaches its uses; theme propagation does
not prove structural linkage. Never temporarily recolor a live shared theme with
unknown consumers for a test. Report untouched scope and untested modes honestly.

Paper-specific UI/MCP mechanics, code and cross-file copy, and current roadmap
boundaries: `../../paper-design/references/themes-and-tokens.md`.
Official source: [Paper tokens](https://paper.design/docs/tokens).
