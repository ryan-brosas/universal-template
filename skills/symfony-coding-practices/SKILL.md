---
name: symfony-coding-practices
description: "Use when authoring or reviewing Symfony PHP, PHP CS Fixer, Yoda identical compares, naming matrix, FQCN services, PHPDoc rules, sprintf exceptions, and MIT license headers."
disable-model-invocation: true
---

# Symfony Coding Practices

Application skill for Symfony official coding standards ingest (`awesome-guidelines`). Generic PHP: `php-coding-practices`. PSR layout overlap shared; Symfony adds Yoda, service ids, and exception prose rules.

## Core Principle

Symfony PHP reads uniformly, **PSR-12 via PHP CS Fixer**, **Yoda identical compares**, **strict naming matrix**, **FQCN service ids**, and **formatted exception/deprecation messages** with MIT headers.

## When to Use / NOT

- Symfony components, bundles, apps, and Symfony-style OSS libraries.
- Configuring PHP CS Fixer with Symfony rule set.
- PR review on Symfony contribution or internal bundle.

**NOT when:**

- Generic PHP without Symfony conventions, `php-coding-practices`.
- Laravel/WordPress-specific style, stack capsules in `foundation-pack/`.
- Runtime Symfony architecture (DI tags, events), framework docs/foundation.

## Workflow

1. **Structure**, spacing, Yoda, control flow, class order (`symfony-style-structure-control.md`).
2. **Naming/services**, case matrix, FQCN ids (`symfony-style-naming-services.md`).
3. **PHPDoc/errors**, docs, exceptions, license (`symfony-style-phpdoc-exceptions.md`).
4. **Verify**, PHP CS Fixer + tests (`symfony-style-verify.md`).

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
- Capsule checklist on exceptions and Yoda compares

## Skill Result Contract

```xml
<skill_result>
  <skill>symfony-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>diff, php-cs-fixer output, test log</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>Yoda miss, service id drift, or exception format regression</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/symfony-style-learning-note.md`
- `awesome-guidelines/references/symfony-style-structure-control.md`
- `awesome-guidelines/references/symfony-style-naming-services.md`
- `awesome-guidelines/references/symfony-style-phpdoc-exceptions.md`
- `awesome-guidelines/references/symfony-style-verify.md`

## Related skills

- `php-coding-practices`, PSR-12, strict_types, DI baseline
- `api-design-practices`, HTTP API adjacent to Symfony routes
- `webappsec-coding-practices`, web security on Symfony apps
