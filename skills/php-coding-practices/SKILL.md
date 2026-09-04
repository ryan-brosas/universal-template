---
name: php-coding-practices
description: "Use when authoring or reviewing PHP, PSR-12 layout, PSR-1/PSR-4 file hygiene, strict_types, identical comparison, typed APIs, visibility, final classes, and constructor injection over singletons."
invocation: manual
disable-model-invocation: true
---

# PHP Coding Practices

Application skill for PHP style learning (from the archived `awesome-guidelines` style capsules). For Laravel/Symfony/WordPress stack patterns, load stack capsules under `skills/*-foundation`.

## Core Principle

PHP readability is **PSR mechanical layout plus strict typed APIs**, side-effect-free autoload files, identical comparison, injected dependencies.

## When to Use / NOT

- PHP application/library source, Composer packages, PHPCS/Pint/PHP-CS-Fixer CI.
- Reviewing namespaces, types, comparison, class design.

**NOT when:**

- Non-PHP code.
- Generated stubs (PHPUnit mocks, protobuf), validate generator config instead.
- CMS-specific rules (WordPress/Drupal), use stack capsules under `skills/*-foundation`.

## Workflow

1. **Format & layout**, PSR-12 indent, braces, imports, LF endings (`php-style-formatting-layout.md`).
2. **Files & namespaces**, PSR-4 side-effect-free files, PascalCase/camelCase (`php-style-files-namespaces.md`).
3. **Types**, `strict_types`, hints, `===`, `??` (`php-style-types-comparisons.md`).
4. **Classes**, visibility, `final`, DI, early return (`php-style-classes-design.md`).
5. **Verify**, PHP-CS-Fixer, Laravel Pint, or PHPCS (PSR-12) + PHPStan/Psalm on changed paths.

## Red Flags

- Closing `?>` in pure PHP class files
- `ini_set` / `echo` in PSR-4 autoloaded class file
- Loose `==` without documented intent
- `$name = null` + `?:` default instead of typed default
- `Singleton::getInstance()` for domain services
- Public mutable properties on domain objects
- Magic numbers in conditionals

## Verification

- `php-cs-fixer fix --dry-run` / `./vendor/bin/pint --test` / PHPCS PSR-12 on changed files
- PHPStan/Psalm at project level on touched namespaces
- Capsule checklist on public API review


## References

- `awesome-guidelines/references/php-style-learning-note.md`
- `awesome-guidelines/references/php-style-formatting-layout.md`
- `awesome-guidelines/references/php-style-files-namespaces.md`
- `awesome-guidelines/references/php-style-types-comparisons.md`
- `awesome-guidelines/references/php-style-classes-design.md`
