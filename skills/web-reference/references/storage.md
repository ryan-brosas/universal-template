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

A quick capture is one region screenshot, `REFERENCE.md`, and `manifest.json` — source URL, capture timestamp, one visual artifact, truthful manifest. Rendered HTML, styles, and fonts are optional for quick mode; declare anything skipped in `coverage_gaps` instead of quietly pretending. Do not create empty placeholder files.

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

Evidence values are booleans or bundle-relative paths, and every declared path must exist. `coverage_gaps` records known omissions for model review. The model decides whether the collected evidence is sufficient for the question; scope labels do not mechanically imply a universal evidence quota.

Capture ids are `YYYY-MM-DD`, or `YYYY-MM-DDTHHMM` when a second capture happens on the same calendar day. Ids must be unique.

## Validation

Inspect `manifest.json` and referenced files with native filesystem and JSON tools. Confirm field types, exact enums, capture identifiers, path containment, file existence, and credential hygiene. `scripts/web-reference-manifest.py` is an optional Python implementation of those hard checks for maintainers and CI. It does not judge coverage, trust, visual quality, or ADOPT / ADAPT / OMIT.

## REFERENCE.md

Decision-oriented and short: why the reference exists, important visual qualities, typography, layout, patterns, motion, responsive and interaction behavior, media roles, then coverage gaps. No design encyclopedia.

ADOPT / ADAPT / OMIT sections belong here when the project has decided how the reference enters implementation — that decision is owned by `reference-driven-development`, not by capture. A capture without decisions yet is valid: state what the site does, and the decision record lands when the reference is consumed.

## Versioning and refresh

- Each capture lands in `captures/<capture-id>/`; the id is the date, or the date plus `T<HHMM>` for a second capture on the same day. Never overwrite an earlier capture.
- `refresh` captures into a new capture-id directory, updates the manifest `captures` list, and reports route, token, pattern, and screenshot changes. Do not diff minified JavaScript by default.
- The live site is current evidence when behavior may have changed; the archive stays historical evidence.

## Storage policy

- Small structured bundles (REFERENCE.md, manifest, design JSON, selected screenshots) may be committed under project policy.
- Raw archives stay out of Git by default: local, ignored, LFS, or an artifact store, per project decision. Inspect size before committing.
- Crawler cache and temp files are discarded after normalization.
- The reference contract lifecycle applies: project-local, read-only, disposable; captures do not promote to skills or foundations.
