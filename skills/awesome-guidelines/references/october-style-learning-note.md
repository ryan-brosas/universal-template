# October CMS coding standards — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `october-style-*.md` capsules, `october-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Developer Guide](https://docs.octobercms.com/1.x/help/developer-guide.html) (primary) | PSR exceptions; naming matrix; views; DB; events; class guidance; MySQL strict |
| [octobercms/october README](https://github.com/octobercms/october) (primary) | PSR-1, PSR-2, PSR-4 baseline |
| [Publishing packages](https://docs.octobercms.com/4.x/extend/resources/publishing-packages.html) (primary) | `-plugin`/`-theme` composer names; semver; `composer/installers` |
| [Available exceptions](https://docs.octobercms.com/3.x/extend/system/exceptions.html) (secondary) | `ApplicationException`, `SystemException`, `ValidationException`, handler placement |
| `php-coding-practices` (secondary) | PSR-12 baseline — October adds marketplace naming + PSR carve-outs |
| `symfony-coding-practices` / Laravel patterns (secondary) | contrast only — October uses Rain/Laravel subset, not full Symfony rules |

**Scope:** **October CMS plugins, themes, and marketplace packages.** Docs are versioned (1.x guide still canonical for naming patterns; 3.x/4.x for exceptions/publishing). **Not:** generic PHP without October conventions, WordPress/Drupal/Magento CMS skills, or full October platform architecture.

## Mental model

October style = **PSR mechanical base + marketplace naming matrix + Rain/Laravel idioms**:

1. **PHP & PSR** — PSR-1/2/4; camelCase variables; snake_case for DB attrs, postback/HTML names, lang keys; controller AJAX methods may use single underscore; `elseif`/`catch` bodies on new lines.
2. **Naming patterns** — `Vendor.Plugin` author codes; tables `author_plugin_*`; components `List`/`Details` suffixes; views `.htm` with `_` partial prefix; events `module.term` global vs local.
3. **Classes & exceptions** — prefer `protected` over `private`; scalar public properties OK; `ApplicationException` for user-facing; `SystemException` for critical; handlers in plugin `boot` or `init.php`.
4. **Packages & verify** — composer name ends `-plugin` or `-theme`; semver releases; MySQL `STRICT_TRANS_TABLES` in dev; PSR + October naming review before marketplace publish.

## Decision tables

### PSR base & exceptions

| Topic | Rule |
|---|---|
| Base | PSR-1, PSR-2, PSR-4 (per october repo README) |
| Variables | camelCase default |
| DB model attributes/relations | snake_case |
| HTML/postback/lang keys | snake_case |
| Controller AJAX | `{action}_onHandler` or `onHandler` — single underscore allowed (PSR exception) |
| Control layout | `elseif` / `catch` opening brace on new line (October preference; PHPCS may need exception) |
| View extension | `.htm` only |

### Vendor, repo, package

| Topic | Rule |
|---|---|
| Vendor/author code | starts uppercase; no underscores/dashes (`Acme.Blog`, not `acme.blog`) |
| Git repo | `blog-plugin` or `oc-blog-plugin`; themes `-theme` suffix |
| Composer package | `vendor/blog-plugin` type `october-plugin`; themes `-theme` + `composer/installers` |
| Semver | required when publishing; protect existing sites from breaking changes |

### Plugin artifact naming

| Artifact | Rule |
|---|---|
| DB tables | `{author}_{plugin}_*`; booleans `is_*` |
| Extended columns | prefix `{author}_{plugin}_` or acronym |
| Controllers (backend) | plural (`Products`, `Categories`) |
| Models | singular (`Product`, `Category`) |
| Components | `List`/`Details` suffix or descriptive non-conflicting name |
| View partials | leading `_`; layouts/controllers without; `-` = space, `_` = folder |
| HTML ids | camelCase or hyphen-case; classes hyphen-case |
| Form names | snake_case |
| Events global | `plugin.module.term`; local omit prefix; pass `$this` first on global |
| Model scopes (chain) | prefix `apply` (ideal), or `is`/`for`/`with`/`filter` |

### Class & exception guidance

| Topic | Rule |
|---|---|
| Visibility | prefer `protected` over `private` for extensibility |
| Scalar property | public OK instead of getter/setter |
| Collection property | protected + get/set helpers |
| User-facing errors | `ApplicationException` (no sensitive paths in message) |
| Critical/system | `SystemException` (logged with detail) |
| Form validation | `ValidationException` with field map |
| Error handlers | register in plugin `boot()` or `init.php` |

### Environment & verify

| Topic | Rule |
|---|---|
| MySQL | enable `STRICT_TRANS_TABLES` in development |
| Review | PSR-2/4 compliance + October naming checklist before marketplace |
| Dependencies | declare in `composer.json`; semver tag releases |

## Anti-patterns

- Lowercase vendor code (`acme.blog`)
- Underscore/dash in author namespace segment
- camelCase database column on model conflicting with `$visible`-style properties
- Boolean column without `is_` prefix when it conflicts with model attrs
- Partial view without leading underscore
- View file not ending in `.htm`
- Component named same as model/controller without suffix
- Event named `onSomething` (use before/after terms)
- Throwing raw `\Exception` for expected user errors
- `SystemException` for validation messages shown to users
- Composer package missing `-plugin`/`-theme` suffix
- Publishing breaking changes without semver major bump
- Private-by-default classes intended as extension base
- Disabling MySQL strict mode during development

## Skill trace

| Artifact | Role |
|---|---|
| `october-style-php-psr.md` | PSR base, camelCase/snake_case split, PSR exceptions |
| `october-style-naming-patterns.md` | vendor, DB, MVC, views, events, components |
| `october-style-class-exceptions.md` | visibility, Rain exceptions, handlers |
| `october-style-packages-verify.md` | composer, semver, MySQL strict, review |
| `october-coding-practices/SKILL.md` | October plugin/theme review workflow |

## Relation to sibling skills

| October standards | php-coding-practices | magento/drupal |
|---|---|---|
| PSR-2 + carve-outs | PSR-12 modern | CMS-specific DI/layers |
| camelCase + snake_case split | consistent camelCase PSR | snake_case heavy |
| Plugin code `Vendor.Plugin` | PSR-4 namespaces | module prefixes |
| `.htm` views | N/A | twig/phtml |

Publishing semver aligns with `git-workflow-and-versioning` / semver capsules in awesome-guidelines cross-cutting ingest.
