# Session-derived behavior tests

These RED cases occurred in real Paper/Figma work; they are not hypothetical style preferences.

| Pressure scenario | Observed RED failure | Required GREEN behavior |
|---|---|---|
| The component set is large and a PNG already matches visually. | The PNG was placed as the Button Group deliverable and called canonical. | Use the PNG only as reference; audit the final JSX for forbidden screenshot rasters. |
| Names, bounds, and counts pass, but screenshots time out and the user says “next.” | The page was called complete and work advanced. | Report `structurally-verified, visual-pending`; do not claim pixel-perfect. |
| A bridge dump is capped at 51 KB and appears to contain three children. | Seven valid blocks were deleted from File Assets. | Detect truncation, split/re-fetch targeted nodes, and snapshot before deletion. |
| A mutation times out after several inner calls. | Mutations were retried and content landed on the wrong page or duplicated. | Inspect page/root state before retrying and pass explicit `fileId`/`pageId`. |
| The source font is unavailable, but a substitute looks close. | The fallback was used while pixel-perfect completion was implied. | Require explicit approval for `approved-fallback`; never certify substitute fonts as pixel-perfect. Missing font evidence must fail the manifest gate. |
| A generic diamond/square is quicker than exporting the source icon. | Vector geometry drifted while structural checks still passed. | Reuse the exact SVG/vector asset and verify the rendered silhouette. |

## Normalization pressure case

An exact `textOverflow` assertion failed although Paper stored a one-line WebKit
clamp and the fresh long-label render truncated correctly. Under deadline pressure,
inspect the compound styles and render rather than replaying the mutation to force
a particular CSS spelling (`../../paper-component-consistency/references/paper-specifics.md`).
Repeat with a visibly overflowing label: do not accept that case merely because
clamp properties exist. Equal paint also remains insufficient proof of a token binding.

## Reuse regression probes

Use an authorized disposable fixture and an existing editable specimen. These
checks distinguish real propagation from labels or shared current values; they
are not a new mandatory runtime workflow.

- Duplicate a token-bound specimen with different content. Change an alias target
  only in the fixture and inspect references plus fresh renders: all bound uses
  should change without changing the original file's theme. This demonstrates
  local token propagation, not cross-file synchronization.
- Change only the fixture owner's layout. Inspect existing copies before updating
  them. If they do not change, propagate an explicit shared-property patch through
  clone mappings and verify content/state overrides survived. Do not call copies
  linked components merely because their colors updated together.
- Exercise short/long labels, optional content, and relevant widths. Compare the
  render before and after the owner-level fitting fix; confirm clipping/wrapping,
  icon lanes, and states rather than only artboard dimensions. A disabled visual
  preview does not establish disabled interaction.

These probes ran against built work during guidance authoring. They establish
fixture behavior, not a controlled before/after measurement of agent task lift.
