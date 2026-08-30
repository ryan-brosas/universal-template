---
name: wordpress-coding-practices
description: "Use when authoring or reviewing WordPress themes/plugins, WPCS PHP naming, Yoda conditions, late esc_* output, $wpdb->prepare, i18n text domains, HTML/CSS/JS handbooks, and PHPCS verification."
disable-model-invocation: true
---

# WordPress Coding Practices

Application skill for WordPress official coding standards ingest (`awesome-guidelines`). Generic PHP: `php-coding-practices`. Accessibility: `wcag-accessibility-practices`. HTML/CSS baseline: `frontend-markup-practices`.

## Core Principle

WordPress maintainability is **ecosystem-safe PHP plus late escaping**, snake_case and Yoda layout, context-matched `esc_*` at output, prepared SQL, translatable strings, and PHPCS-enforced handbooks across PHP/HTML/CSS/JS.

## When to Use / NOT

- WordPress themes, plugins, mu-plugins, and core-style contributions.
- Reviewing hooks, templates, `$wpdb` usage, admin screens, block editor assets.
- Setting up PHPCS with `WordPress-Core` / `WordPress-Extra` rulesets.

**NOT when:**

- Non-WordPress PHP, `php-coding-practices`.
- Vendored third-party libraries inside a plugin, exempt from WPCS per handbook.
- Full plugin architecture (CPT, REST, blocks), WordPress foundation docs.

## Workflow

1. **PHP naming/layout**, snake_case, Yoda, files, hooks (`wordpress-style-php-naming.md`).
2. **Security/escape**, late output escaping per context (`wordpress-style-security-escape.md`).
3. **Database/i18n**, prepare SQL, gettext strings (`wordpress-style-database-i18n.md`).
4. **Assets/verify**, HTML/CSS/JS + PHPCS + a11y (`wordpress-style-assets-verify.md`).

## Red Flags

- camelCase PHP functions or variables
- Shorthand PHP tags or missing `ABSPATH` guard in plugin files
- Non-Yoda literal comparison (`$x === 'foo'`)
- Raw SQL with interpolated variables
- Quoted `%s`/`%d` inside `$wpdb->prepare()`
- `echo $var` without context-appropriate escape
- `extract()` on request/query arrays
- `@` error suppression instead of proper handling
- Missing text domain in new `__()` / `_e()` strings
- Unquoted HTML attributes
- camelCase CSS selectors or over-qualified `div.class`
- snake_case JavaScript variable names
- PHPCS WordPress violations on changed PHP paths

## Verification

- `phpcs --standard=WordPress` (or project ruleset) on changed `.php` files
- ESLint/JSHint on changed admin/block JS where configured
- Manual spot-check: escape at echo, prepare placeholders unquoted
- i18n grep: new user strings use text domain + translator comments
- WCAG AA checklist on changed UI (`wcag-accessibility-practices`)

## Skill Result Contract

```xml
<skill_result>
  <skill>wordpress-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>diff, phpcs output, optional eslint log</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>unescaped output, unprepared SQL, or i18n miss</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/wordpress-style-learning-note.md`
- `awesome-guidelines/references/wordpress-style-php-naming.md`
- `awesome-guidelines/references/wordpress-style-security-escape.md`
- `awesome-guidelines/references/wordpress-style-database-i18n.md`
- `awesome-guidelines/references/wordpress-style-assets-verify.md`

## Related skills

- `php-coding-practices`, PSR baseline outside WordPress
- `wcag-accessibility-practices`, WCAG AA UI depth
- `frontend-markup-practices`, generic HTML/CSS habits
- `javascript-coding-practices`, JS outside WP admin conventions
- `webappsec-coding-practices`, broader secure coding patterns
