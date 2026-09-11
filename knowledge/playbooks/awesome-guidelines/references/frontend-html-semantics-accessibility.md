<!-- capsule-v2 -->
# HTML semantics — is this the right element for structure and accessibility?

**Source:** Google HTML/CSS §Semantics, §Multimedia; Code Guide §Practicality. **Question:** Does markup communicate purpose without CSS/JS?

## Semantics seam
**Path/Symbol:** page template / component HTML.
**Signature:** `<!doctype html>`, `<meta charset="utf-8">`, `<html lang="…">`.
**Data Shape:** semantic elements; attributes for identity (`class`, `data-*`), not behavior in markup.

### Decisive contrast
```html
<!-- Wrong -->
<div onclick="goToRecommendations()">All recommendations</div>
<img src="chart.png">

<!-- Right -->
<a href="recommendations/">All recommendations</a>
<img src="chart.png" alt="Q3 revenue chart.">
```

**Flow:** choose native element for purpose → add `lang`/charset/doctype → provide `alt`/labels → keep presentation out of HTML.
**Invariant:** structure serves accessibility and reuse — buttons are `<button>`, links are `<a href>`, headings use `h1–h6`.
**Probe:** W3C validator clean (or documented exceptions); axe/lighthouse a11y on images/controls; no inline `style` for layout in templates.

## Separation seam
**Flow:** HTML = structure only → CSS files for presentation → JS files for behavior → minimal linked assets per template.
**Invariant:** changing theme/layout must not require editing HTML templates beyond class hooks.
**Probe:** grep templates for `style=` and `onclick=` near zero; styles live in stylesheets.

## Verdict
Adopt semantic HTML + alt text + concern separation; omit div soup and presentational markup. Learning note: `frontend-style-learning-note.md`.
