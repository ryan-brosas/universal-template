# Media: roles, generation, provenance

## Roles, not assets

Record what each visual does before anything else. Manifest entries:

```json
{"role": "hero-visual", "reuse": "omit", "replacement": "generate", "notes": "large dark product visualization"}
{"role": "background-treatment", "reuse": "adapt", "replacement": "css"}
```

`reuse: omit` means the captured asset stays evidence only. Presence in the archive grants no reuse rights: logos, brand names, marketing copy, product screenshots, and distinctive illustration are omitted by default.

## Decision flow per required visual

1. Can CSS do it cleanly (gradient, border, shadow, blend)? Use CSS.
2. Does the project already have a fitting asset? Reuse it.
3. Is a reference asset legitimately reusable (license, permission)? Rare; record provenance.
4. Otherwise generate an original.

## Image generation

Probe the host for a media capability; on pi hosts the `openai_image` extension tool (pi-better-openai) generates and edits images with project-local save. Do not hard-code model slugs in project policy: the configured default owns model choice, and a `model` argument is passed only when the user or project config names one.

Brief template (reference qualities, never the source asset):

```
role: hero illustration
visual direction: dark technical interface, soft volumetric glow
must fit: 1440px hero, right side of layout
reference qualities: low saturation, deep contrast, soft lighting
do not copy: reference product, logo, brand illustration
```

Editing (remove background, extend, recolor, recompose) applies to generated or project-owned assets only; do not mutate captured proprietary media into near-copies.

## Output

- Location: the project asset directory (`public/`, `assets/`, `src/assets/` per project convention), never `reference/web/`.
- Formats: alpha needs PNG or WebP; photographic fits WebP or JPEG; icons and simple shapes prefer SVG or CSS.
- Optimize before shipping: dimensions, compression, responsive variants, lazy loading.
- Provenance sidecar next to the asset (`<name>.media.json`): provider, date, prompt or brief, dimensions, purpose. No secrets in it.
- Misleading product shots: prefer real product screenshots; generated mock UI only when conceptual or explicitly requested.
