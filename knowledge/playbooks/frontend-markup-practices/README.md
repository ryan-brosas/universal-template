---
title: frontend-markup-practices
summary: Use when authoring or reviewing static HTML/CSS, semantic markup, accessibility, class-based low-specificity CSS, js-* hooks, formatting, HTTPS assets, and validation; distilled from Google HTML/CSS, CSS Guidelines, and Code Guide.
kind: playbook
---

# Frontend Markup Practices

Application skill for HTML/CSS. For React/TS component patterns, inspect current project frontend code and any project-local `reference/` or `reference/web/` assets first; then consult the framework's own source or docs.

## Core Principle

**Structure in HTML, presentation in CSS, behavior in JS**, with explicit, reusable class selectors and separate JS hooks so refactors do not cross wires.

## When to Use / NOT

- Static templates, email HTML, design-system CSS, or pre-framework markup review.
- Auditing selector specificity, a11y alt text, or asset loading.

**NOT when:**

- TypeScript/React implementation: inspect current project components/tokens, then relevant `reference/web/` or code references, then `typescript-coding-standards`, or the framework's own source or docs.
- Stack-specific UI kit already owns conventions, project wins.

## Workflow

1. **Markup**, doctype, charset, `lang`, semantic elements, meaningful `alt`, no inline presentation (`frontend-html-semantics-accessibility.md`).
2. **Naming**, hyphenated purpose classes; no `#id` selectors; selector intent; `.js-*` for behavior only (`frontend-css-naming-selectors.md`).
3. **Structure**, 2-space formatting, grouped declarations, media queries beside rules, component-scoped files (`frontend-css-structure-formatting.md`).
4. **Delivery**, HTTPS assets, avoid `@import`, validate HTML/CSS (`frontend-assets-delivery.md`).
5. **Verify**, validator + a11y spot check + Stylelint/style guide config.

## Red Flags

- `<div onclick>` / missing `alt`.
- `#id` or `header ul` styling.
- Same class used for CSS and JS binding.
- Protocol-relative or HTTP CDN URLs on HTTPS sites.
- Reactive `!important` sprawl.

## Verification

- W3C HTML/CSS validator (or CI equivalent) on changed templates.
- Lighthouse/axe on representative pages.
- Stylelint rules aligned with the project config.
- Grep: `.js-` absent from CSS; `@import` absent from production entry CSS.
