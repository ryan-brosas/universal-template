# Themes and CSS-variable tokens

Sources: [Tokens](https://paper.design/docs/tokens),
[MCP](https://paper.design/docs/mcp), and the
[build log](https://paper.design/build-log). Reviewed 2026-09-06.

For source identity, aliases, inherited Figma modes, consumer scope, and safe
propagation verification, use `../../pencil/references/tokens.md`. That reference
owns the transfer policy; this one supplies Paper's concrete mechanics.

## What exists

Paper tokens are CSS custom properties shared by canvas styles and exported code.
Supported categories: color, radius, spacing, container, breakpoint, font family,
font weight, font size, line height, and letter spacing. Inspect current tools for
accepted names/types and normalization rather than guessing a prefix from a label.

The docs still put these on the roadmap:

- Bundled theme classes, such as one H1 style applying several typography properties.
- Multiple native theme modes, such as dark or compact values for the same token.
- Shared libraries; cross-file copies currently do not synchronize.

Do not flatten independent Figma mode axes into one global switch. If native support
is absent, use explicitly labeled previews or verified scoped values under the
existing transfer policy; previews are not live modes. Breakpoint/container tokens
supply values, not automatic media queries or responsive components.

## Theme tab operations

- **Create:** Theme tab → add → choose token type → name/value. Closing the modal
  or clicking elsewhere saves automatically.
- **Apply:** choose the token in the property dropdown; colors also expose a
  four-circle token picker. Inspect the stored reference, not just the visible value.
- **Edit:** select the token in Theme, change name/value, click elsewhere to save.
  All bound uses should update. Right-click Duplicate makes a separate token.
- **Detach:** color properties have a detach button; other dropdowns have Detach
  or Backspace. The current value remains, but the dependency is removed.
- **Delete:** select tokens in Theme, right-click Delete. Determine consumers and
  recovery before deletion; the docs do not establish a safe dependent-alias policy.

## Three sources, one chosen owner

**From Figma:** connect both MCPs in the same host and confirm both file identities.
Select an element using the relevant variables/styles. Inspect source bindings,
alias closure, and resolved modes. Clipboard paste alone does not create equivalent
Paper bindings. Transfer only dependencies needed by the selected work.

**From code:** read the actual CSS-variable source and its imports, selectors,
mode scopes, units, and aliases. Inventory existing Paper tokens, reconcile names,
then create/update missing or changed entries. Do not make a light-only snapshot
look like an imported multi-mode system. Preserve Tailwind's version-specific owner;
Paper's conceptual Tailwind mapping does not justify inventing an `@theme` block.

**From a Paper frame:** ask the agent to derive the requested categories from the
selected design. Inspect whether values are recurring decisions or incidental
geometry. Token generation is a proposal until ownership and actual bindings are
verified; it need not tokenize every number.

## Agent operations

Discover the installed tool schemas. At review time these operations were exposed:

| Operation | Use / inspect |
|---|---|
| `get_tokens` | Filter categories or names; request JSON, CSS, or Tailwind output |
| `create_tokens` | Create entries; values can alias another token with `var(--name)` |
| `set_tokens` | Update, rename, or delete by full CSS-variable name |
| `find_nodes` | Find literal or token usages; page-scoped unless scoped to a subtree |
| `update_styles` / `write_html` | Bind properties using CSS variables |

Pass explicit file identity where supported. Inspect **each entry's result**:
batches can succeed at the transport level while individual entries fail. Inspect
`ignoredStyles` on style updates. Read back generated CSS names before binding.

A literal-color search can also return token-bound usages, and a match inside a
border/gradient is only a fragment. Read the complete property before replacing it.
Search relevant pages and transitive aliases; an empty current-page result is not
a file-wide consumer audit. Do not apply a global color-to-token substitution:
equal colors can represent distinct semantic decisions.

## Small example (illustrative values, not a project palette)

These CSS declarations show the intended relationships; they are not a claim that
pasting a stylesheet creates Theme entries. Create entries through the supported
UI/MCP, confirm their emitted names, then bind the editable frame.

```css
:root {
  --color-brand: #2457e7;
  --color-action: var(--color-brand);
  --color-on-action: #ffffff;
  --spacing-control: 12px;
  --radius-control: 8px;
}
```

```html
<div layer-name="Action specimen"
  style="display:flex; padding:var(--spacing-control); border-radius:var(--radius-control); background-color:var(--color-action); color:var(--color-on-action);">
  <div layer-name="Label">Continue</div>
</div>
```

This is a canvas specimen, not an accessible button implementation. In an isolated
fixture, inspect references, change the primitive, and confirm both direct and
aliased consumers render the new value. Also verify spacing/radius consumers;
color-only success does not test the whole theme. Do not temporarily recolor a live
shared theme with unknown consumers.

## Reconnecting a pasted template

Before treating a pasted or duplicated file as customizable, distinguish:

- **Tokens exist:** Theme entries are present.
- **Properties are bound:** editable nodes store references to the intended entries.
- **Theme works:** changing an owner token reaches the expected direct and aliased consumers without per-node repainting.

Check all three. Inventory detached literals by semantic role within the requested scope, not by color equality alone. Reconnect a representative property to an existing token while preserving its intended resolved appearance; then use an authorized theme change or isolated fixture to demonstrate propagation. Repeat for the non-color categories being customized. Batch equivalent binding repairs only after the representative check passes.

Inspect gradients, borders, SVG paints, and text overrides separately when they are in scope; matching a frame background does not prove its nested assets or text are bound. Preserve intentional literals and unsupported properties as named exceptions. Do not tokenize every coordinate, force all artwork into the brand palette, or claim token-copying establishes cross-file synchronization.

For applying project branding to a duplicate, use `../../paper-project-branding/SKILL.md`. This workflow does not require a new import or a parallel token system.

## Copying out and between files

In Theme, right-click a token → Copy. Cmd+A selects the full set; Shift selects
multiple. Paste in another Paper file to copy tokens, or into the codebase's CSS
theme file to copy declarations. Inspect the result before merging code changes.
June's build log also describes File menu → Theme → Copy theme / Paste theme;
prefer the current visible UI when menu placement changes.

Copies in different Paper files **do not update together**. Check alias closure,
name collisions, and destination bindings after paste; the docs do not promise
collision/merge semantics. Copying tokens does not prove existing destination
nodes bind to them. For repeated synchronization, compare against the chosen owner
and apply explicit diffs; do not alternate uncontrolled writes between Figma,
Paper, and code.

Acceptance: stored references, resolved values, relevant consumer propagation,
font rendering, and intended export names/units agree. Report untested modes and
copy-only dependencies separately.
