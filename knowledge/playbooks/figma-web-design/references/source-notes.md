# Source notes and limits

This draft adapts workflow ideas from **Figma Mastery for Web Designers**, using
course transcripts supplied for the earlier extraction. It does not include the
course's assets, exercise files or UI kits. No redistribution rights for those
materials were established; obtain the appropriate permission before reuse.

Useful lesson anchors include **Organizing Figma Files & Layers**, **Layout Grids
for Web Design**, **Variables vs. Local Styles**, **Building Components**, and
**Figma Blueprints (Your Project Starter)**. The reusable ideas are a permitted
project starter, explicit component/variable relationships, and inspection of
the final deliverable. Local transcript paths and extraction progress are not
part of the published procedure.

## Adaptation decisions

- Existing project assets, naming and bindings take precedence over course
  examples. Numeric scales, page skeletons and component sizes are illustrative,
  not permission to create a replacement design system.
- Prices, subscription limits, named plugins and UI3-specific controls are not
  treated as current requirements.
- Variable modes select or inherit values; they are not CSS responsive clamps.
  Verify the intended mode separately from frame resizing.
- Detachment removes the main-component relationship; inspect variable/style
  bindings separately rather than assuming they were removed too.
- Normal auto-layout children use auto-layout sizing. Constraints apply to
  children that ignore that flow.

## Current documentation

- [Variable modes](https://help.figma.com/hc/en-us/articles/15343816063383-Modes-for-variables)
- [Applying variables](https://help.figma.com/hc/en-us/articles/15343107263511-Apply-variables-to-designs)
- [Auto layout](https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout)
- [Instance API and detachment](https://developers.figma.com/docs/plugins/api/InstanceNode/)

No live Figma workflow or before/after task comparison has been measured for this
draft. Do not claim demonstrated task lift or design fidelity from prose alone.
The supplied course material did not include its advertised dedicated auto-layout
module; use current documentation and real task evidence rather than inventing
that missing lesson.
