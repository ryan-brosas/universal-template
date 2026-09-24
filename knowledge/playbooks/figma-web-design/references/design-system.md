# Design system foundations

Inspect and reuse the source system first. When creation of a missing system is
explicitly authorized, build **variables, then bound styles, then components**.
The course examples below are not replacement values for an existing system.

## Layers of the system

1. **Tokens (variables)** - a single value: colour, size, threshold. Grouped by area in separate collections: colours, typography, spacing/gaps, borders and radii, shadows.
2. **Styles (local/global styles)** - composite presets that reference tokens: colour styles, text styles, effect styles, grid styles.
3. **Components and UI patterns** - buttons, cards, inputs, menus, modals, alerts, sections. Because they reference tokens and styles, updating a token propagates through them.
4. **Project assets** - logos, icon libraries, imagery direction. Always project-specific; the blueprint only reserves a page for them.

## Naming

Preserve the source names and aliases. For an approved new system, lower-case
hierarchical names with t-shirt sizing are one option; keep the design/code
mapping explicit. These are examples, not a required renaming scheme.

- Type: `text/m`, `text/l`, `header/xl`, plus `xxs`/`xs` where needed.
- Space: `gap/s`, `gap/m`.
- Shape: `radius/xs` through `radius/xl`.
- Effects: `shadow/s`, `shadow/m`.
- Colour: `primary/500`, `accent/300`, `neutral/900`.

The naming is the contract: consistent tokens are what let a design map onto a real site without re-interpretation.

## Variables versus local styles

- A **variable** is one metric, reusable across styles, components, and individual properties. Changing it updates everything bound to it.
- A **local style** is a composite preset, for example a heading style containing size, weight, line height, and letter spacing.
- Bind variables *into* styles rather than typing raw numbers. A text style should reference type tokens, not hold its own pixel values.
- Creating both is one-time duplicate work; it pays back on the first project change and again on every handoff.
- Prefer variables wherever the variable control appears - layout-grid gutters and margins included, so grid metrics are tokens rather than loose numbers.

## Colour tokens

- Scale: `primary/100` to `primary/900`, with `500` as the base shade; the scale leaves room for intermediate steps such as `primary/50` or `primary/150`.
- Roughly four to five steps cover most projects; nine is a generous maximum, not a requirement.
- **Neutral** carries text and background colours - whites, greys, blacks. Pick a neutral base towards the middle of the scale so it has contrast headroom in both directions.
- **Accent** is for highlights and hover states and should be used sparingly; it pairs naturally with the primary for interactive feedback.
- **Semantic** colours (error, success, warning) matter most in forms and product UI; they are a small part of a marketing site.
- One secondary colour is enough for most projects; extra secondaries exist to keep the system scalable, not to be used by default.
- Create a colour style on top of each colour variable for convenient picking, then organise the styles into folders (primary, accents, neutrals).

## Modes

A collection can carry **modes**, such as light/dark or desktop/mobile values.
Bound properties resolve the selected or inherited mode; this is not a CSS
`clamp()` or an automatic width breakpoint. Preserve source modes and test
selection/inheritance separately from frame resizing. See Figma's
[modes documentation](https://help.figma.com/hc/en-us/articles/15343816063383-Modes-for-variables).

## Avoid

- Mixing raw values and tokens for the same property, which produces two parallel palettes that drift apart.
- Restricting discovery to **created in this file** before inspecting the enabled
  source libraries; that can hide the variables the deliverable must reuse.
- Editing a bound value in place instead of the token; bindings must be detached first, and detaching silently breaks the system.

## Starter number collections

Course examples for an explicitly authorized new system. Existing source values,
modes and aliases take precedence; do not create these collections by default.

| Collection | Members and starter values |
| --- | --- |
| `gaps` | `xxs` 4, `xs` 8, `s` 12, `m` 20 (base), `l` 40, `xl` 60, `xxl` 80. Mobile mode flattens the large end (for example `xxl` 20) so big desktop spacing does not survive onto phones. |
| `content width` | 350, 500, 750, 1000 px, applied as a max width to paragraphs and narrow sections; add project-specific values as they come up. |
| `borders` | radius `none` 0, `xs` 2, `s` 4, `m` 8, `l` 12-20, `xl` 24-40, `full` 100 (pill); border width `s` 1, `m` 2, `l` 4. Keep border widths to about three. |
| `box shadows` | one cluster per size (`xs`-`xl`), each holding `x`, `y`, `blur`, `spread` as numbers plus a shadow colour at 15-25 percent opacity. A base medium is `x` 0-2, `y` 10, `blur` 40, `spread` -4. |
| `icon avatar width` | 12, 16, 24, 40 (base), 60, 80, 120; bind height to the same token. |
| `opacity` | 10, 15, 20 and upward to 95, for overlays and imagery. |
| `spacing` | section padding, with `top/bottom` and `left/right` as separate variables per size. Left/right is commonly 80 px on desktop and 20 px on mobile; top/bottom scales from a compact section up to a banner. |
| `typography` | per role: font family (string), font weight (number), font size (number) with desktop and mobile modes. |

Apply these numbers where the tool offers a variable control, including auto-layout gaps and the layout grid's gutters and margins. A value typed by hand is a value that will drift.

## Type scale

A course example in px (desktop/mobile), not a required scale or accessibility
guarantee. Reuse source typography; tune new values only within an approved
system-design task and verify legibility and accessibility.

| Role | Sizes |
| --- | --- |
| Header | `xxl` 72/52, `xl` 52/42, `l` 42/32, `m` 32/24, `s` 24/20, `xs` 20/20, `xxs` 20 |
| Body text | `xxl` 32/24, `xl` 24, `l` 20, `m` 16 (base), `s` 14, `xs` 12, `xxs` 10 |
| Button text | `l` 16, `m` 16, `s` 14, `xxs` 12 - never larger, buttons do not need display sizes |

- **Line height:** about 100 percent for large display type, 110-125 percent for mid sizes, and up to 150-175 percent for body and buttons. Smaller text takes proportionally more line height.
- **Buttons:** 150 percent line height as a rule, with centre and middle alignment baked into the text style so every button inherits it.
- **Weights:** 300 light, 400 regular, 500 medium, 600 semibold, 700 bold, 800 extrabold, 900 black. Use at most two families; one is usually enough.
- Small text often should not shrink on mobile, and is occasionally larger there, because phones are harder to read.

## Effect styles

- Reuse source **box shadow styles** when the design uses shadows. An approved
  new system needs only the shadow sizes its actual components require.
- **Background blur** produces glassmorphism and needs a fill above zero opacity. Blur tokens of 2, 4, 8, and 12 cover the common cases.
- **Inner shadow and layer blur** serve skeuomorphic or one-off graphic needs. Add them per project when the design calls for them rather than shipping them in every blueprint.
- Organise effect styles into folders such as box shadows and blurs.

## Caveat to verify

Figma can discard a variable value typed without confirming it. Check that a value actually saved before building on top of it, especially during bulk entry.

## Creation mechanics

Traps when an approved system is written into a file through the MCP plugin API.

- **Dynamic-page documents reject the synchronous setters.** Assigning `node.textStyleId`
  raises `Cannot call with documentAccess: dynamic-page`; use
  `await node.setTextStyleIdAsync(id)`. A script that fails mid-way leaves partial
  artifacts behind, so remove the leftovers before retrying rather than building on them.
- **`resize()` discards a hug.** Calling `resize()` on an auto-layout frame resets that
  axis to FIXED, so a sizing mode set before the resize is silently undone and the frame
  clips or overflows its children. Set the sizing modes after resizing, and sweep every
  auto-layout frame in the build, because the trap is per frame: fixing the outer one hides
  it deeper in, as a hero frame that hugged correctly while its content frame stayed fixed.
- **Promoting a node to a component reissues its id.** `createComponentFromNode` returns
  a new node. Capture name and size before the call and do not touch the old handle
  afterwards, or the next property read throws "node does not exist".
- **Reassign paints returned by `setBoundVariableForPaint`.** It returns a new paint
  object, so map the fills or strokes array and assign the result back.
- **Preserve the source multiplier.** Line height and tracking stored as CSS multipliers
  map to Figma PERCENT (1.02 becomes 102 percent) and survive a font-size change; pixel
  values bake in the size they were written at.
- **Check installed font weights before adopting a scale.** A token calling for a 600
  weight cannot be honoured when the family ships only Light, Regular, Medium and Bold.
  Choose the nearest installed weight, record the substitution, and keep it consistent
  between the text styles and any mark that carries live text.
- **Style ids are write-only here.** `setTextStyleIdAsync` exists, but `getTextStyleIdAsync`
  is absent and the synchronous `textStyleId` returns an empty string, so an applied style
  cannot be read back. Verify by resolved values instead (font family and weight, size,
  line height percentage, letter-spacing), which is stronger evidence than the style name.
- **Check a placed library component for default slots.** An icon button can ship with
  its left and right icon slots both filled, so a freshly instantiated button may carry two
  icons. Read `componentProperties` and switch the unwanted slot off through the exposed
  property rather than deleting the instance child.
- **Resolve variables by collection, never by bare name.** Token names repeat across
  collections (`sm`, `md` and `lg` exist as both spacing and radius), so a flat
  name-to-variable map binds whichever entry was read last. A spacing property bound to a
  radius token reads `2` where the scale says `16`, and the write still reports success.
  Key the lookup by collection plus name, and assert the collection when verifying.
- **A negative geometry result must name its predicate.** A clipping check that compares a
  child's size against its parent's content box tests one mechanism only; overflow is a
  question about absolute bounds against the bounds of the nearest clipping ancestor, and
  neither catches a clip inside a library component or at render time. State the mechanism
  tested and what it excludes, instead of reporting that nothing clips.
- **Verify bindings by resolving them, not by trusting the write.** Read each node's bound
  variable ids back to names and confirm they are the intended token, especially where a
  mark mixes one accent stroke among otherwise neutral ones.
- **Imported vectors carry a background fill.** A mark imported from SVG sits on an opaque
  plate until the frame's fills are cleared, which breaks its use on dark or photographic
  surfaces.
