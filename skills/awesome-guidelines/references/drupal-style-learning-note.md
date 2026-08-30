# Drupal coding standards — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `drupal-style-*.md` capsules, `drupal-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Drupal Coding Standards](http://project.pages.drupalcode.org/coding_standards/) (primary index) | Version-independent always-current rules; US English; fix by rule not file |
| [PHP coding standards](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/php/coding.md) (primary) | 2-space indent, 80 cols, naming, control, operators, type hints, strict_types |
| [Namespaces](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/php/namespaces.md) (primary) | `Drupal\module_name\...`, PSR-4 under `src/`, use/import rules |
| [API documentation](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/php/documentation.md) (primary) | DocBlocks, `@param`/`@return`, `{@inheritdoc}`, hook summaries |
| [YAML configuration files](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/yaml/configuration-files.md) (primary) | `.yml` naming, 2-space indent, extension-prefixed config names |
| [Twig coding standards](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/twig/coding.md) (primary) | Template docblocks, `{% if %}`, attributes drillable pattern |
| [JavaScript coding standards](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/javascript/coding.md) (primary) | 2-space, semicolons, file closure IIFE, camelCase, ESLint/Airbnb |
| [CSS format](https://git.drupalcode.org/project/coding_standards/-/raw/main/docs/css/format.md) (secondary) | 2-space, LF endings, docblock comments for rulesets |
| `php-coding-practices` (secondary) | PSR baseline — Drupal uses 2 spaces (not PSR-12 4), module-prefixed procedural functions |
| `wcag-accessibility-practices` (secondary) | Accessibility handbook stub points to WCAG work in Drupal contrib/core |

**Scope:** **Drupal modules, themes, profiles, and core-style PHP/YAML/Twig/JS/CSS.** Canonical docs live on **GitLab Pages** (`project.pages.drupalcode.org/coding_standards`); drupal.org wiki pages are **obsolete/archived**. **Not:** generic PHP without Drupal conventions, full Drupal architecture (entity/API design — use Drupal foundation).

## Mental model

Drupal style = **always-current cross-version rules + PSR-4 OOP + procedural module prefix discipline**:

1. **PHP layout & naming** — 2 spaces, no tabs, 80-char target; `module_name_function()` procedural; UpperCamelCase classes; lowerCamelCase methods/properties; short array `[]`; no closing `?>`; `elseif` not `else if`.
2. **Namespaces & types** — `Drupal\module_name\...` mapped to `module/src/`; one class per file; `use` imports (no leading `\`); type hints on all new methods; interface type hints preferred.
3. **Documentation & i18n** — `/** */` docblocks on every class/method/file; hook summaries `Implements hook_foo().`; user strings via `t()` / `@Translation`; US English spelling.
4. **Config & assets & verify** — YAML 2-space; Twig docblocks + `{{ attributes }}`; JS IIFE + `Drupal.behaviors`; PHPCS Drupal + PHPStan + ESLint in CI.

## Decision tables

### PHP — layout & naming

| Topic | Rule |
|---|---|
| Indent | 2 spaces, never tabs |
| Line length | target 80 characters |
| Procedural functions | lowercase + underscores + **module prefix** |
| Variables | lowerCamelCase **or** snake_case — pick one per file, never mix |
| Classes / interfaces / traits | UpperCamelCase; suffix `Interface`, `Trait`, `Test` |
| Methods / properties | lowerCamelCase; no `_` prefix for visibility |
| Constants | `MODULE_NAME_CONSTANT`; prefer `const` keyword |
| Arrays | short syntax `[]`; trailing comma on multi-line |
| PHP tags | full `<?php`; **omit closing `?>`** in `.module`/`.php` files |
| Control | always braces; `elseif` not `else if`; space after keyword before `(` |
| Operators | spaces around binary ops; `?:` and `??` encouraged where readable |
| Includes | `require_once` unconditional; `include_once` conditional; no parens on path |

### Namespaces & types (Drupal 8+)

| Topic | Rule |
|---|---|
| Module namespace | `Drupal\module_name\SubFolder\ClassName` |
| File path | `module_name/src/SubFolder/ClassName.php` |
| Global classes | prefix `\` when used (`new \DateTime()`) — do not `use` globals |
| Namespaced classes | `use` at top; one class per `use`; FQCN in strings without leading `\` |
| New code | parameter + return type hints; `void` when no return; interface over class hint |
| strict_types | `declare(strict_types=1);` after file docblock when used |

### Documentation & translation

| Topic | Rule |
|---|---|
| Docblock | `/**` on every file, class, method (incl. private), constant |
| Summary | ≤80 chars, capital start, period end; third-person for classes |
| Hooks | `Implements hook_help().` — omit param/return docs |
| Override | `{@inheritdoc}` when identical to parent |
| Types in tags | PHPDoc types: `int`, `bool`, `array`; FQCN with leading `\` |
| User strings | `t('String', [], ['context' => '...'])` — US English in source |

### YAML / Twig / JS / CSS

| Layer | Rule |
|---|---|
| YAML | `extension.name.yml`; 2-space indent; machine-name prefixes |
| Twig | `{# @file docblock #}`; `{% if var %}`; print `class` explicitly + `{{ attributes }}` |
| JS | file wrapped in IIFE; `Drupal.behaviors`; semicolons required; eslint-config-airbnb |
| CSS | 2-space; kebab/BEM-style component naming in core; LF endings; file header comment |

## Anti-patterns

- Tabs in PHP/YAML/CSS/JS
- Mixing camelCase and snake_case variables in one file
- Procedural function without module prefix (collision risk)
- Class named `DrupalSomethingClass` or containing "Drupal" in class name
- Interface without `Interface` suffix (or non-interface with suffix)
- Public mutable properties on services/entities
- Closing `?>` in PHP module files
- `else if` instead of `elseif`
- Missing docblock on new public method
- `@param` type without leading `\` for namespaced class
- Raw English string in UI without `t()`
- YAML config name not prefixed with owning extension
- Twig template missing trailing `{{ attributes }}` when printing individual attrs
- Global JS variables outside closure
- PHPCS/PHPStan failures on changed PHP paths

## Skill trace

| Artifact | Role |
|---|---|
| `drupal-style-php-naming.md` | layout, naming, control, operators |
| `drupal-style-namespaces-types.md` | PSR-4, use, type hints, interfaces |
| `drupal-style-documentation-i18n.md` | docblocks, hooks, t() |
| `drupal-style-assets-verify.md` | YAML, Twig, CSS/JS, PHPCS |
| `drupal-coding-practices/SKILL.md` | Drupal review workflow |

## Relation to sibling skills

| Drupal standards | php-coding-practices | wordpress-coding-practices |
|---|---|---|
| 2-space indent | PSR-12 4-space | tab indent |
| UpperCamelCase classes | PascalCase PSR | `Class_Name` underscores |
| No Yoda conditions | identical `===` | Yoda required |
| `?:` short ternary OK | neutral | short ternary forbidden |
| PSR-4 `module/src` | PSR-4 Composer | `class-wp-error.php` |
| PHPCS Drupal + PHPStan | PHP-CS-Fixer PSR-12 | PHPCS WordPress-Core |

Framework patterns: Drupal foundation docs when present.
