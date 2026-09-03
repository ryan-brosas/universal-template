# Paper tokens from Figma

Create tokens **before** the first `write_html` of a component. `create_tokens` names must match `^--[a-zA-Z0-9_-]+$`.

## Variables to the bone

If Figma defines a variable, copy that variable. Do not stop at the resolved color.

1. Call `get_variable_defs` (figma-bridge). Collections, modes, names, values, aliases.
2. For each variable the copied frame binds (fill, stroke, padding, radius, font size, gap), create a Paper token.
3. Name: Figma path to kebab with `--`. `Color/Primary/Default` becomes `--color-primary-default`. Slashes and spaces become `-`. Drop illegal characters.
4. Alias stays an alias: Figma alias of another variable becomes `var(--that-token)`, not a second hex.
5. Value is the **active mode** (the mode on the file or the selection). Do not pick a different mode because it looks nicer.
6. HTML and `update_styles` use `var(--token)` for every bound property.
7. Mint a raw hex/px token **only** when that property has no Figma variable.

`get_node` styles that still say `#6f61ff` are not a license to skip the variable. Check whether the paint is bound. If it is, the Paper name follows Figma, not a homemade `--color-primary`.

Paper tokens are CSS variables ([docs/tokens](https://paper.design/docs/tokens)). Types: color, radius, spacing, container, breakpoint, font family, font weight, font size, line height, letter spacing. Theme classes and multiple theme modes are on the Paper roadmap, not shipping. Copy the **active** Figma mode only. Do not invent a dark-mode set.

Tokens are per file. Copying tokens to another Paper file does not keep them in sync. Figma paste into Paper detaches variables, so MCP `create_tokens` is the path that keeps names.

## Order (server rule)

1. Color: neutrals first, then primary, secondary, accent.
2. Spacing, radius, fontSize: smallest value first.
3. Reuse `var(--other)` for aliases. Do not mint a second primary.

## Fallback set (no Figma variable on that property)

Use this table only for Button properties that `get_variable_defs` does not cover. If Atomize already has a variable, that name wins and this row is skipped.

| name | type | value |
|---|---|---|
| `--color-bg` | color | `#ffffff` |
| `--color-text` | color | `#0a0c11` |
| `--color-text-muted` | color | `#8c929c` |
| `--color-text-disabled` | color | `#c3c6cc` |
| `--color-disabled-bg` | color | `#f2f2f4` |
| `--color-primary` | color | `#6f61ff` |
| `--color-primary-on` | color | `#ffffff` |
| `--color-primary-on-muted` | color | `rgba(255,255,255,0.72)` |
| `--color-primary-light` | color | `rgba(111,97,255,0.12)` |
| `--color-primary-light-text` | color | `#5548d8` |
| `--space-gap-in` | spacing | `2px` |
| `--space-gap-icon` | spacing | `6px` |
| `--space-gap-label` | spacing | `12px` |
| `--space-gap-set` | spacing | `24px` |
| `--space-pad-set` | spacing | `40px` |
| `--radius-xs` | radius | `6px` |
| `--radius-sm` | radius | `8px` |
| `--radius-md` | radius | `10px` |
| `--radius-lg` | radius | `12px` |
| `--radius-xl` | radius | `14px` |
| `--radius-set` | radius | `40px` |
| `--text-xs` | fontSize | `10px` |
| `--text-sm` | fontSize | `13px` |
| `--text-lg` | fontSize | `15px` |
| `--text-xl` | fontSize | `18px` |
| `--button-col` | container | `297px` |
| `--font-ui` | fontFamily | installed family (Figma: Open Sauce Two; Paper often only Inter) |

Use `var(--token)` in HTML. If a Figma value is missing, `get_node` that variant. Do not guess. Do not invent a parallel palette beside the copied variables.

## After create_tokens

`get_basic_info` must list them. Later types (success, danger) add semantic colors; they do not replace `--color-primary` unless Figma does.
