---
name: magento-coding-practices
description: "Use when authoring or reviewing Adobe Commerce/Magento extensions, strict_types, PSR-12,::class, DI/composition, prepared SQL, escape output, service contracts, and PHPCS Magento2 verification."
invocation: manual
disable-model-invocation: true
---

# Magento Coding Practices

Application skill for Adobe Commerce / Magento Open Source coding standards ingest (`awesome-guidelines`). Generic PHP: `php-coding-practices`. Security depth: `webappsec-coding-practices`. Sibling CMS: `drupal-coding-practices`, `wordpress-coding-practices`.

## Core Principle

Magento extension quality is **PSR-12 mechanics plus Magento2 PHPCS security sniffs plus technical-guideline architecture**, strict typed PHP, interface DI and composition, layered service contracts, sanitize/escape discipline, and static analysis in CI.

## When to Use / NOT

- Adobe Commerce / Magento Open Source modules under `app/code/Vendor/Module`.
- Reviewing `di.xml`, `*Api` interfaces, controllers, blocks, `.phtml`, module JS.
- Setting up PHPCS `Magento2`, ESLint, PHPMD in extension CI.

**NOT when:**

- Non-Magento PHP, `php-coding-practices`.
- WordPress/Drupal, sibling CMS practice skills.
- Core platform refactors spanning entire Magento tree, follow Adobe core contribution process.
- Hyvä/headless frontends only, still apply API/security rules; JS/CSS guides may differ.

## Workflow

1. **PHP/types**, strict_types, return types,::class (`magento-style-php-types.md`).
2. **Class/DI**, composition, constructors, di.xml (`magento-style-class-di.md`).
3. **Security/exceptions**, SQL, XSS, superglobals, exceptions (`magento-style-security-exceptions.md`).
4. **Layers/verify**, Api modules, docblocks, PHPCS (`magento-style-layers-verify.md`).

## Red Flags

- New PHP file missing `declare(strict_types=1);`
- String literal class name instead of `::class`
- Missing return type on new public method
- `$_GET` / `$_POST` / `$_SERVER` in module code
- Unescaped output in PHP (outside vetted `.phtml` patterns)
- Public `init()` or business logic in constructor
- Concrete adapter type-hinted in constructor instead of interface
- Deep inheritance for code reuse
- Raw SQL with interpolated variables
- Swallowed exception without logging
- Generic `\Exception` thrown from controller
- Stateful plugin or plugin on data object
- Object instantiation inside `.phtml` template
- PHPCS Magento2 errors on changed extension paths

## Verification

- `vendor/bin/phpcs --standard=Magento2 app/code/Vendor/Module` on changed paths
- `vendor/bin/phpcbf --standard=Magento2` for auto-fixable sniffs
- ESLint with magento-coding-standard config on changed JS
- PHPMD project ruleset when available
- DocBlock spot-check on new public API
- di.xml preference/plugin review for new services


## References

- `awesome-guidelines/references/magento-style-learning-note.md`
- `awesome-guidelines/references/magento-style-php-types.md`
- `awesome-guidelines/references/magento-style-class-di.md`
- `awesome-guidelines/references/magento-style-security-exceptions.md`
- `awesome-guidelines/references/magento-style-layers-verify.md`

## Related skills

- `php-coding-practices`, PSR baseline outside Magento
- `webappsec-coding-practices`, broader secure coding patterns
- `symfony-coding-practices`, DI/Yoda patterns in Symfony stacks (contrast)
- `drupal-coding-practices`, sibling CMS conventions
- `wordpress-coding-practices`, sibling CMS conventions
