# Spread the Paper file

Do not rip a Figma file onto one Paper page. Match Figma's own split.

## Mapping

| Figma | Paper |
|---|---|
| one `.fig` / design file | one Paper file (reuse the open file) |
| one Figma **page** (Cover, Buttons, Input fields) | one Paper **page** (`create_page`, then `open_file` with `pageId`) |
| one top-level **frame or component set** on that page | one **artboard** |
| variants inside a component set | rows/cells on that artboard |

Tokens stay file-scoped. Create them once. Every page reuses `var(--color-primary)`.

## Atomize example

Figma `↪ Buttons` children are sibling frames, not one collage:

- `Overview-sheet` (docs chrome)
- `Button` (180 variants)
- `Icon-button`
- `Button-success`
- `Button-danger`
- `Tip`

Paper:

1. Page **Cover**: existing cover + tip only.
2. Page **Buttons**: artboard `Button`, artboard `Icon-button`, artboard `Button-success`, artboard `Button-danger`. Optional artboard `Overview-sheet` if you copy the docs chrome.
3. Later, page **Input fields**, page **Toggle**, and so on. Same pattern.

Derive artboard positions and spacing from the active source. An automatic
placement default is not source evidence. For an exact transfer, preserve source
coordinates and grouping; use project-approved spacing only where the source
leaves placement unspecified. Do not nest unrelated component sets merely to
save space.

## Example order of work on a page

Open the target page before mutations. Independent sibling work may be batched
when verified tools support it; the sequence below is not a global requirement.

1. `create_page` named after the Figma page. `open_file` to that page.
2. Artboard for the first component set. Copy until it matches Figma.
3. Next artboard for the next sibling set. Same tokens, new bounds.
4. Do not append Icon-button rows under the Button set to "save a page".

## What stays together

Variants of **one** component set (primary xs-xl, four states) stay on that set's artboard. That is Figma's grouping. Mixing Button with Icon-button is not.
