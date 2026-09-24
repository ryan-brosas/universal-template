# Components and variants

A component is any reusable element: a button at the small end, a whole hero section at the large end. The component library is the third leg of the blueprint, after tokens and styles.

## Workflow

1. Search enabled libraries, local components and the approved blueprint first.
   Reuse a suitable instance. Only when new component creation is authorized,
   build the missing element on the components page, not inside a screen.
2. Bind its text, colour, radius, spacing, and shadow to the existing styles and tokens.
3. Create the component, then reuse it from the assets panel with the library filtered to its approved source, or by inserting an instance.
4. Edit the main component only when a system-wide change is intended and
   authorized; use exposed properties for local content and variant changes.

Repeated elements are a reason to check for a shared component, not permission
to create a replacement for an existing library asset.

## Variants

- Start from one component, then add a variant to create a variant set: a parent component containing one nested component per option.
- Rename the properties coherently so the set reads as a scale, for example `button/xl`, `button/l`, `button/m`, `button/s`.
- Use the existing size variants and matching text styles. Add a size only for
  an approved requirement the source set cannot meet.
- Add colour as a second axis (light and dark) rather than multiplying sizes.
- Size each variant by its padding and its button text style rather than by hand-tuned values, so the variants stay consistent with the tokens.

## Instances and overrides

- An instance can be overridden, and the override stays local to that instance.
- **Push changes to main component** sends an instance override to every instance in the file. It is powerful and destructive; prefer editing the main component deliberately.
- **Reset** can also discard custom labels, icon choices and other intentional
  overrides. Identify the faulty field and use the smallest supported correction.
  Capture required content and actions before any broader reset; a component swap
  may preserve the override that caused the defect.
- **Detach instance** removes the main-component relationship and its future
  component updates. Variable and style bindings are separate and may remain;
  inspect them independently. Do not detach to bypass the source component.

## Audit configured instances

Use this when controls remain linked but look or behave differently. Compare a
known-good example of the same role with the reported defect before sweeping the
file. Distinguish the shared component set, selected variant, exposed visibility
and swap properties, internal overrides, and the enclosing layout. An optional
arrow can be correctly linked yet hidden by either its slot or icon property.
Verify the actual visible icon as well as the property values.

Repair the lowest shared owner authorized for that role. Capture labels, swaps,
responsive sizing and destinations first. Read back both that source and its real
consumer instances: nested slot overrides can mask a successful source edit.
Resolve full instance paths and their main components rather than assuming a short
slot-override ID is the editable source. Avoid changing a global primitive to fix
one page's configuration.

Compare variable identities and consumer-resolved modes before numerical values.
Desktop and mobile text may legitimately resolve different sizes through the same
alias. Read the spacing scale rather than inferring a value from its name or ID.
Check HUG/FILL/fixed sizing and growth in the delivered layout; a source's nominal
height can stretch in its consumer, and resizing a HUG node need not persist the
requested width. Verify bounds and text overflow after configuration changes.

For swapped monochrome action icons, preserve the icon's native filled or stroked
geometry. Use the owning control slot's existing semantic color where appropriate;
copying a placeholder's filled channel onto an outline icon changes its shape.
Compare resolved RGBA with the label and surface, including disabled states.
A shared color variable can resolve different alpha values across modes; distinguish
that from a raw opacity override. Inspect stale explicit mode pins before changing
global tokens. Multicolor assets and intentionally contrasting icons need their
own expected pairing.

Preserve interaction ownership. Native hover should match the selected variant,
unless an enclosing section intentionally owns it. Page-specific navigation must
retain the correct breakpoint destination. Source and consumer edits can combine
stale hover overrides or duplicate navigation; inspect again after each level's
change. Do not copy a source-page navigation target blindly into another page.

Treat unavailable fonts as an operation-specific constraint. In an official remote
editor, changing existing variant or icon properties succeeded while text editing
and configured-instance insertion required unavailable fonts. Local installation
does not prove remote availability. Continue independently supported configuration
work, preserve labels and report text repairs separately. Do not repeat an unchanged
failed call, substitute fonts without authorization, or use a full reset to bypass
a text-editing failure.

Verify ownership, approved role configuration, appearance, layout and interactions
separately on actual consumers. Pair native property/binding readback with fresh
renders. Turn objective escapes, such as a required icon being hidden, into checks
at the existing project verifier; keep role-selection judgment with the approved
reference. A passing ownership count is evidence for ownership only.

## Library scale

A mature library splits across pages by pattern (nav, hero, cards, footer) rather than living in one long list, and it grows: production kits ship dozens of nav variants and hundreds of hero variants. Expect the components page to be reorganised as the library grows, and build sections as components early rather than retrofitting later.

## Naming

Component and variant names should match the token and style names (`button text/l`, `gap/m`). The naming is what lets a developer map a design onto real classes or custom properties without translation.