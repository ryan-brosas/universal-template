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

## Fidelity manifest

Save one JSON manifest per completed artboard:

```json
{
  "status": "pixel-perfect",
  "target": { "fileId": "...", "pageId": "...", "nodeId": "..." },
  "artifacts": {
    "sourceScreenshot": "/absolute/source.png",
    "paperScreenshot": "/absolute/paper.png",
    "diffImage": "/absolute/diff.png",
    "structuralAudit": "/absolute/structure.json"
  },
  "structure": { "nameMismatches": 0, "boundsMismatches": 0, "countMismatches": 0 },
  "assets": { "flattenedScreenshotRefs": 0, "componentImageRefs": 3 },
  "fonts": { "unavailable": [], "fallbackApproved": false },
  "visual": { "status": "passed" },
  "theme": { "status": "passed" }
}
```

Font evidence is explicit: `fonts.unavailable` is a list of nonempty font names
(empty only when none are unavailable), and `fonts.fallbackApproved` is a boolean.
Missing or malformed fields are not proof that fonts are available.

The validator checks evidence completeness. Human inspection still decides whether
the render actually matches. Test the font boundary with
`python3 skills/pencil/scripts/test-verify-fidelity-manifest.py` from the repository root.
