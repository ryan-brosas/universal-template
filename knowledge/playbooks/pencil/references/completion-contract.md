# Paper Copy Completion Contract

This contract exists because editable structure can pass while the design is visibly wrong.

## Page transaction

Before mutating:

1. Confirm the Figma file/page/node IDs.
2. Open the intended Paper `fileId` and `pageId`.
3. Read the root artboards and detect duplicate pages.
4. Snapshot JSX for every node that may be removed or replaced.
5. Pass `fileId` to every mutation.

After a timeout, inspect the target page before retrying. Fabric may report an outer failure after an inner Paper mutation succeeded. Never replay a mutation from the error alone.

## Evidence states

| State | Required evidence |
|---|---|
| `built` | Editable target layers exist. |
| `structurally-verified` | Exact names, counts, bounds, text, vectors, and approved image assets. |
| `visually-verified` | Fresh source and Paper renders plus an inspected comparison/diff. |
| `pixel-perfect` | Structural + visual + token/theme + font gates all pass. |
| `approved-fallback` | User explicitly accepted a named deviation such as a substitute font. Never call this pixel-perfect. |

A dead screenshot bridge cannot produce `visually-verified` or `pixel-perfect`. Preserve the editable work, report `visual-pending`, and stop.

## Asset classes

- **Allowed:** the actual source IMAGE fill used by a component, exported SVG/vector geometry, logos, and photography required by the source.
- **Forbidden:** a screenshot or raster export of the page, artboard, component set, row, or component used instead of editable layers.

A raster audit must classify references. A blanket “zero raster files” rule is wrong when the Figma component genuinely contains an image.

## Completion evidence

Record the evidence in the project's existing design notes or task report:

- Source and destination file/page/node identities, with the scope compared.
- Fresh source and Paper renders plus the inspected comparison or diff.
- Structural checks for names, counts, bounds, text, and editable asset provenance.
- Token references, resolved values, and observed theme propagation.
- Actual source-font availability and rendering; name unavailable fonts and any
  explicitly approved fallback. Missing font evidence blocks a pixel-perfect claim.
- Remaining differences, unverified states, and the completion state justified by
  these observations.

Inspect the artifacts themselves. A list of evidence paths or a stated pass does
not establish that the render matches. An approved fallback remains a named
deviation, not pixel-perfect completion.
