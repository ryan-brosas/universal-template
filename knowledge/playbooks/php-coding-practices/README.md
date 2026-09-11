---
title: php-coding-practices
summary: Use when authoring or reviewing PHP, PSR-12 layout, PSR-1/PSR-4 file hygiene, strict_types, identical comparison, typed APIs, visibility, final classes, and constructor injection over singletons.
kind: playbook
---

# PHP Coding Practices

Application skill for PHP style. For Laravel/Symfony/WordPress stack patterns, load the framework's own source or docs.

## Core Principle

PHP readability is **PSR mechanical layout plus strict typed APIs**, side-effect-free autoload files, identical comparison, injected dependencies.

## When to Use / NOT

- PHP application/library source, Composer packages, PHPCS/Pint/PHP-CS-Fixer CI.
- Reviewing namespaces, types, comparison, class design.

**NOT when:**

- Non-PHP code.
- Generated stubs (PHPUnit mocks, protobuf), validate generator config instead.
- CMS-specific rules (WordPress/Drupal), use the framework's own source or docs.

## Workflow

1. **Format & layout**, PSR-12 indent, braces, imports, LF endings.
2. **Files & namespaces**, PSR-4 side-effect-free files, PascalCase/camelCase.
3. **Types**, `strict_types`, hints, `===`, `??`.
4. **Classes**, visibility, `final`, DI, early return.
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
