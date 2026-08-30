# Storage: bundle layout, manifest, versioning

## Layout (create only what the mode earns)

```text
reference/web/<host>/
├ REFERENCE.md
├ manifest.json
├ captures/
│  └ <capture-id>/      # YYYY-MM-DD, or YYYY-MM-DDTHHMM for a second capture on the same day
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
  "coverage_gaps": ["interactions: hover states not captured"],
  "captures": [
    {"id": "2026-08-31", "archive": "captures/2026-08-31/raw/site.wacz"},
    {"id": "2026-08-31T1435"}
  ]
}
```

Evidence values are booleans or bundle-relative paths. Every declared path must exist. A known key marked `false` needs a `coverage_gaps` entry that names it. Expected evidence by scope: quick, page, and site captures need `rendered_html` and `screenshots`; deep additionally needs `computed_styles` and `css_variables`. An expected key that is absent needs a matching `coverage_gaps` entry too.

Capture ids are `YYYY-MM-DD`, or `YYYY-MM-DDTHHMM` when a second capture happens on the same calendar day. Ids must be unique.

## Validation

```bash
python3 ~/.agents/scripts/web-reference-manifest.py reference/web/<host>
```

P0 findings fail the check: missing manifest or REFERENCE.md, a manifest that is not a JSON object, bad fields, referenced files that do not exist, evidence values that are neither boolean nor path, expected evidence missing without a declared gap, invalid or duplicate capture ids, REFERENCE.md without ADOPT / ADAPT / OMIT decision section headers, credential-like material, undeclared partial capture. Warnings: oversized files, duplicate routes, missing viewports on site captures, credential scans truncated by file size.

## REFERENCE.md

Decision-oriented and short: why the reference exists, important visual qualities, typography, layout, patterns, motion, responsive and interaction behavior, media roles, then ADOPT / ADAPT / OMIT per concern, then coverage gaps. No design encyclopedia.

## Versioning and refresh

- Each capture lands in `captures/<capture-id>/`; the id is the date, or the date plus `T<HHMM>` for a second capture on the same day. Never overwrite an earlier capture.
- `refresh` captures into a new capture-id directory, updates the manifest `captures` list, and reports route, token, pattern, and screenshot changes. Do not diff minified JavaScript by default.
- The live site is current evidence when behavior may have changed; the archive stays historical evidence.

## Storage policy

- Small structured bundles (REFERENCE.md, manifest, design JSON, selected screenshots) may be committed under project policy.
- Raw archives stay out of Git by default: local, ignored, LFS, or an artifact store, per project decision. The validator warns above 25 MB.
- Crawler cache and temp files are discarded after normalization.
- The reference contract lifecycle applies: project-local, read-only, disposable; captures do not promote to skills or foundations.
