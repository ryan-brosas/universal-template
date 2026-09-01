---
name: drupal-coding-practices
description: "Use when authoring or reviewing Drupal modules/themes, 2-space PHP layout, module-prefixed functions, PSR-4 namespaces, docblocks, t() i18n, YAML/Twig/JS standards, and PHPCS/PHPStan verification."
disable-model-invocation: true
---

# Drupal Coding Practices

Application skill for Drupal official coding standards ingest (`awesome-guidelines`). Generic PHP: `php-coding-practices`. WordPress CMS: `wordpress-coding-practices`. Accessibility: `wcag-accessibility-practices`.

## Core Principle

Drupal maintainability is **always-current handbook discipline plus typed PSR-4 services**, two-space layout, module-prefixed procedural code, documented APIs, translatable strings, and PHPCS/PHPStan-enforced conventions across PHP, YAML, Twig, and JS.

## When to Use / NOT

- Drupal modules, themes, profiles, and contrib/core-style patches.
- Reviewing `src/`, `.module`, `config/*.yml`, `.html.twig`, module JS/CSS.
- Setting up PHPCS Drupal + PHPStan + ESLint in GitLab CI or local dev.

**NOT when:**

- Non-Drupal PHP, `php-coding-practices`.
- WordPress themes/plugins, `wordpress-coding-practices`.
- Entity design, routing, or migration architecture, Drupal foundation docs.
- Obsolete drupal.org wiki copies, use GitLab Pages canonical docs.

## Workflow

1. **PHP layout/naming**, 2-space, prefixes, casing (`drupal-style-php-naming.md`).
2. **Namespaces/types**, PSR-4, use, hints (`drupal-style-namespaces-types.md`).
3. **Documentation/i18n**, docblocks, hooks, t() (`drupal-style-documentation-i18n.md`).
4. **Assets/verify**, YAML, Twig, JS, CI (`drupal-style-assets-verify.md`).

## Red Flags

- Tabs in PHP, YAML, CSS, or JS
- Mixed camelCase and snake_case variables in one file
- Procedural function missing module prefix
- Class name containing "Drupal" or "Class" suffix misuse
- Interface/Trait/Test suffix violations
- Closing `?>` in module PHP files
- `else if` instead of `elseif`
- Missing type hints on new public methods
- Undocumented public class method
- Raw English UI string without t()
- Config YAML not prefixed with owning extension
- Twig tag missing trailing `{{ attributes }}` when splitting attrs
- JavaScript outside file closure or global variable leak
- PHPCS Drupal or PHPStan failure on changed paths

## Verification

- `phpcs --standard=Drupal` (or project ruleset) on changed PHP
- PHPStan at project level on touched `src/` namespaces
- ESLint on changed `.js` files (eslint-config-airbnb)
- stylelint on changed CSS where configured
- Docblock spot-check on new hooks/classes
- WCAG checklist on changed UI (`wcag-accessibility-practices`)


## References

- `awesome-guidelines/references/drupal-style-learning-note.md`
- `awesome-guidelines/references/drupal-style-php-naming.md`
- `awesome-guidelines/references/drupal-style-namespaces-types.md`
- `awesome-guidelines/references/drupal-style-documentation-i18n.md`
- `awesome-guidelines/references/drupal-style-assets-verify.md`

## Related skills

- `php-coding-practices`, PSR baseline outside Drupal
- `wordpress-coding-practices`, sibling CMS conventions
- `wcag-accessibility-practices`, accessible Drupal UI
- `frontend-markup-practices`, generic HTML/CSS habits
- `javascript-coding-practices`, JS outside Drupal admin patterns
- `yaml` / config patterns, generic YAML hygiene where applicable
