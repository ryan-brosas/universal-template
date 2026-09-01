---
name: october-coding-practices
description: "Use when authoring or reviewing October CMS plugins/themes, PSR-1/2/4, camelCase/snake_case split, marketplace naming, Rain exceptions, composer -plugin/-theme packages, and semver publish verification."
disable-model-invocation: true
---

# October CMS Coding Practices

Application skill for October CMS developer guidelines ingest (`awesome-guidelines`). Generic PHP: `php-coding-practices`. Sibling CMS: `magento-coding-practices`, `drupal-coding-practices`, `wordpress-coding-practices`.

## Core Principle

October maintainability is **PSR layout plus marketplace naming discipline**, camelCase PHP with snake_case at persistence/UI boundaries, consistent plugin codes and table prefixes, Rain exception types, and semver-backed composer packages.

## When to Use / NOT

- October CMS plugins, themes, and marketplace-bound packages.
- Reviewing `Plugin.php`, models, backend controllers, components, `.htm` views, migrations.
- Preparing `composer.json` for `-plugin`/`-theme` publish.

**NOT when:**

- Non-October PHP, `php-coding-practices`.
- Other CMS stacks, sibling CMS practice skills.
- Pure Laravel apps without October plugin structure.
- Client-hosted legacy October 1.x without composer plugins, adapt naming; publishing rules may differ.

## Workflow

1. **PHP/PSR**, PSR base, camelCase/snake_case, AJAX carve-outs (`october-style-php-psr.md`).
2. **Naming**, vendor, DB, MVC, views, events (`october-style-naming-patterns.md`).
3. **Classes/exceptions**, visibility, Rain exceptions (`october-style-class-exceptions.md`).
4. **Packages/verify**, composer, semver, MySQL strict (`october-style-packages-verify.md`).

## Red Flags

- Lowercase or dashed vendor/plugin code (`acme.blog`)
- camelCase DB column conflicting with model property names
- Boolean DB column without `is_` prefix when clash risk exists
- Partial view missing the leading `_`
- View not using `.htm` extension
- Component name colliding with model/controller
- Event named with `onSomething` instead of before/after semantics
- Generic `\Exception` for user-facing validation message
- SystemException for simple form validation users should see
- Composer package name missing `-plugin` or `-theme` suffix
- Breaking API change shipped as patch/minor semver tag
- All-private class intended as extension base
- MySQL strict mode disabled during active schema development

## Verification

- PHPCS PSR-1/2 on changed plugin PHP (document October control-flow exceptions)
- Naming checklist: vendor code, tables, views, components, events
- `composer.json` name/type/suffix review before publish
- Semver tag + version file bump alignment
- MySQL `STRICT_TRANS_TABLES` enabled in dev environment
- Exception type spot-check on new throw sites


## References

- `awesome-guidelines/references/october-style-learning-note.md`
- `awesome-guidelines/references/october-style-php-psr.md`
- `awesome-guidelines/references/october-style-naming-patterns.md`
- `awesome-guidelines/references/october-style-class-exceptions.md`
- `awesome-guidelines/references/october-style-packages-verify.md`

## Related skills

- `php-coding-practices`, PSR baseline outside October
- `git-workflow-and-versioning`, semver for published packages
- `magento-coding-practices`, sibling commerce CMS conventions
- `drupal-coding-practices`, sibling CMS conventions
- `wordpress-coding-practices`, sibling CMS conventions
