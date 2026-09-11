---
title: symfony-coding-practices
summary: Use when authoring or reviewing Symfony PHP, PHP CS Fixer, Yoda identical compares, naming matrix, FQCN services, PHPDoc rules, sprintf exceptions, and MIT license headers.
kind: playbook
---

# Symfony Coding Practices

Application skill for Symfony official coding standards. Generic PHP: `php-coding-practices`. PSR layout overlap shared; Symfony adds Yoda, service ids, and exception prose rules.

## Core Principle

Symfony PHP reads uniformly, **PSR-12 via PHP CS Fixer**, **Yoda identical compares**, **strict naming matrix**, **FQCN service ids**, and **formatted exception/deprecation messages** with MIT headers.

## When to Use / NOT

- Symfony components, bundles, apps, and Symfony-style OSS libraries.
- Configuring PHP CS Fixer with Symfony rule set.
- PR review on Symfony contribution or internal bundle.

**NOT when:**

- Generic PHP without Symfony conventions, `php-coding-practices`.
- Laravel/WordPress-specific style, the framework's own source or docs.
- Runtime Symfony architecture (DI tags, events), framework docs.

## Workflow

1. **Structure**, spacing, Yoda, control flow, class order.
2. **Naming/services**, case matrix, FQCN ids.
3. **PHPDoc/errors**, docs, exceptions, license.
4. **Verify**, PHP CS Fixer + tests.

## Red Flags

- php-cs-fixer diff on changed PHP
- Loose `==` without documented reason
- Literal on RHS in comparisons (`$x === 'foo'` not Yoda)
- else/elseif after return/throw branch
- break after return in switch case
- Spaces inside array offset brackets
- Missing use import for namespaced class
- camelCase config parameter or route name
- Twig template not snake_case
- Abstract class without Abstract prefix (new code)
- Primary service id not FQCN
- Backticks in exception message
- Exception message missing terminal period
- `$obj::class` in exception string (use get_debug_type)
- One-line PHPDoc block
- Missing MIT license header before namespace
- void return type on PHPUnit test method

## Verification

- `vendor/bin/php-cs-fixer fix -v --dry-run` on changed paths
- PHPUnit on touched components
- License header on new files
- debug:container for new service ids


## Related skills

- `php-coding-practices`, PSR-12, strict_types, DI baseline
- `api-and-interface-design`, HTTP API adjacent to Symfony routes
- `webappsec-coding-practices`, web security on Symfony apps
