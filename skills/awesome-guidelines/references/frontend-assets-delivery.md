<!-- capsule-v2 -->
# Assets and delivery — are charset, HTTPS, and load path correct?

**Source:** Google HTML/CSS §Protocol, §Encoding; Code Guide §Avoid @import, §Character encoding. **Question:** Will assets load securely and without extra blocking requests?

## Encoding & HTTPS seam
**Path/Symbol:** `<head>` metadata and asset URLs.
**Signature:** `<meta charset="utf-8">`; explicit `https:` on external CSS/JS/fonts.
**Data Shape:** UTF-8 files; no BOM; literal Unicode in source.

### Decisive contrast
```html
<!-- Wrong -->
<script src="//ajax.googleapis.com/ajax/libs/jquery/3.4.0/jquery.min.js"></script>
<link rel="stylesheet" href="http://fonts.googleapis.com/css?family=Open+Sans">

<!-- Right -->
<meta charset="utf-8">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.0/jquery.min.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Open+Sans">
```

**Flow:** declare UTF-8 → use HTTPS URLs → omit redundant `type` on link/script (HTML5 defaults) → validate HTML/CSS baseline.
**Invariant:** protocol-relative and HTTP assets on HTTPS pages are review rejects.
**Probe:** grep `src="//` and `http://` in templates (except localhost docs); charset meta present.

## CSS loading seam
```html
<link rel="stylesheet" href="core.css">
<!-- not @import url("more.css") in another sheet for critical path -->
```
**Flow:** prefer `<link>` tags or build-time bundle concat → avoid runtime `@import` chains.
**Invariant:** `@import` adds sequential requests and failure modes — not for production critical CSS.
**Probe:** production CSS entry has no top-level `@import` (or build strips them).

## Verdict
Adopt UTF-8 + HTTPS + link-based CSS; validate markup/stylesheets. Learning note: `frontend-style-learning-note.md`.
