# PHP style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `php-style-*.md` capsules, `php-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [PSR-1: Basic Coding Standard](https://www.php-fig.org/psr/psr-1/) | `<?php`/`<?=` only; UTF-8 no BOM; declare symbols **or** side effects, not both; PSR-4 autoload; StudlyCaps classes; UPPER_SNAKE constants; camelCase methods |
| [PSR-12: Extended Coding Style](https://www.php-fig.org/psr/psr-12/) | 4-space indent; LF endings; omit closing `?>`; 120 soft / 80 preferred line length; header block order; import groups; brace placement; control-structure spacing; short type keywords |
| [Clean Code PHP](https://github.com/piotrplenik/clean-code-php) (secondary) | `===`/`!==`; `??`; type hints + defaults; early return; private/protected members; prefer `final`; DI over singleton; no global mutation; named constants over magic numbers |
| [PHP: The Right Way — Design Patterns](https://phptherightway.com/pages/Design-Patterns.html) (secondary) | Prefer dependency injection over singleton global state; singleton reduces testability |

**Not duplicated here:** WordPress/Drupal/Magento CMS coding standards — use stack foundation when CMS is known. Full SOLID treatise — capsules capture review probes only.

## Mental model

PHP style in this catalog is **PSR mechanical layout + modern PHP strictness + Clean Code API habits**:

1. **File hygiene** — pure PHP files omit closing tag; one class per file under PSR-4 namespace; no mixed declare+side-effect files.
2. **Layout** — 4-space indent, Unix LF, PSR-12 header order (`declare` → `namespace` → `use` groups → code), braces on same line for classes/methods, visibility on all members.
3. **Types** — `declare(strict_types=1);` on new code; short keywords (`bool`, `int`); return types and nullable `?Type`; identical comparison `===` for semantics.
4. **Design** — constructor injection over singletons; `final` by default; early return to limit nesting; visibility minimal (`private` until proven otherwise).

## Decision tables

### Files & namespaces (PSR-1)

| Topic | Rule |
|---|---|
| Tags | `<?php` or short echo `<?=` only |
| Encoding | UTF-8 without BOM |
| Side effects | declare symbols **or** execute logic — not both in one autoloaded file |
| Classes | StudlyCaps / PascalCase; one top-level class per file |
| Namespace | vendor-level minimum; PSR-4 path mapping |
| Constants | `UPPER_SNAKE_CASE` |
| Methods | `camelCase()` |

### Formatting (PSR-12)

| Topic | Rule |
|---|---|
| Indent | 4 spaces, no tabs |
| Line endings | LF only; file ends with single LF |
| Line length | soft 120; prefer wrap at 80 |
| Keywords/types | lowercase `true`, `false`, `null`, `int`, `bool`, … |
| Imports | one blank line between `use` groups (classes, functions, consts) |
| Closing tag | omitted in pure PHP files |
| Statements | one per line |

### Types & comparisons (Clean Code + PSR-12)

| Case | Rule |
|---|---|
| Equality | `===` / `!==` unless intentional coercion documented |
| Null default | `??` over nested `isset` ternaries |
| Strictness | `declare(strict_types=1);` first statement after `<?php` |
| Defaults | typed parameter defaults (`string $x = 'foo'`) not null-coalesce hacks |
| Return | declare return types on public API |

### Class design (Clean Code + PHPTRW)

| Case | Rule |
|---|---|
| Visibility | default private/protected; public only for API |
| Extension | prefer composition; `final` unless designed for subclass |
| Globals | no singleton for shared config — inject dependencies |
| Side effects | functions do one thing; no hidden global mutation |
| Arguments | ≤3 parameters; use value objects when growing |

## Anti-patterns

- `<?` short open tags or closing `?>` in class files
- `include 'config.php'` that echoes output inside a PSR-4 class file
- `if ($a == $b)` when types may differ
- `function foo($x = null) { $x = $x ?: 'default'; }` without type hint
- Service `getInstance()` singleton for testable domain code
- Public `$property` on domain objects without intent
- Magic numbers (`448`, `7`) instead of named constants

## Skill trace

| Artifact | Role |
|---|---|
| `php-style-formatting-layout.md` | PSR-12 indent, braces, control flow, imports |
| `php-style-files-namespaces.md` | PSR-1 files, side effects, namespaces, naming |
| `php-style-types-comparisons.md` | strict_types, hints, ===, ?? |
| `php-style-classes-design.md` | visibility, final, DI, early return |
| `php-coding-practices/SKILL.md` | when/how to run PHP-CS-Fixer/Pint/PHPCS |
