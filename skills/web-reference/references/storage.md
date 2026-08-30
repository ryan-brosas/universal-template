# Storage: bundle layout, manifest, versioning

## Layout (create only what the mode earns)

```text
reference/web/<host>/
├ REFERENCE.md
├ manifest.json
├ captures/
│  └ 2026-08-31/
│     ├ raw/            # site.wacz when a site archive was earned
│     ├ pages/<slug>/   # rendered.html, styles.json, links.json, source.html
│     └ screenshots/
├ design/               # deep mode: tokens.json, typography.json, spacing.json
├ patterns/             # named repeated structures, one short markdown each
└ interactions/         # state captures when interaction evidence was needed
```

A quick capture can be one page directory, one screenshot, `REFERENCE.md`, and `manifest.json`. Do not create empty placeholder files.

## manifest.json

```json
{
  "type": "web-reference",
  "source": "https://example.com",
  "captured_at": "2026-08-31T00:00:00Z",
  "scope": "site",
  "viewports": ["desktop", "mobile"],
  "pages": [
    {"route": "/", "path": "captures/2026-08-31/pages/home",
     "screenshots": ["captures/2026-08-31/screenshots/home-desktop.png"]}
  ],
  "evidence": {
    "archive": "captures/2026-08-31/raw/site.wacz",
    "screenshots": true,
    "rendered_html": true,
    "computed_styles": true,
    "css_variables": true,
    "interactions": false
  },
  "media": [
    {"role": "hero-visual", "reuse": "omit", "replacement": "generate",
     "notes": "large dark product visualization"}
  ],
  "coverage_gaps": ["hover states not captured"],
  "captures": [
    {"date": "2026-08-31", "archive": "captures/2026-08-31/raw/site.wacz"}
  ]
}
```

Evidence values are booleans or bundle-relative paths. Every declared path must exist; evidence marked `false` or absent requires matching entries in `coverage_gaps`.

## Validation

```bash
python3 ~/.agents/scripts/web-reference-manifest.py reference/web/<host>
```

P0 findings fail the check: missing manifest or REFERENCE.md, bad fields, referenced files that do not exist, credential-like material, undeclared partial capture. Warnings: oversized files, duplicate routes, missing viewports on site captures.

## REFERENCE.md

Decision-oriented and short: why the reference exists, important visual qualities, typography, layout, patterns, motion, responsive and interaction behavior, media roles, then ADOPT / ADAPT / OMIT per concern, then coverage gaps. No design encyclopedia.

## Versioning and refresh

- Each capture lands in `captures/<date>/`; never overwrite an earlier capture.
- `refresh` captures into a new dated directory, updates the manifest `captures` list, and reports route, token, pattern, and screenshot changes. Do not diff minified JavaScript by default.
- The live site is current evidence when behavior may have changed; the archive stays historical evidence.

## Storage policy

- Small structured bundles (REFERENCE.md, manifest, design JSON, selected screenshots) may be committed under project policy.
- Raw archives stay out of Git by default: local, ignored, LFS, or an artifact store, per project decision. The validator warns above 25 MB.
- Crawler cache and temp files are discarded after normalization.
- The reference contract lifecycle applies: project-local, read-only, disposable; captures do not promote to skills or foundations.
