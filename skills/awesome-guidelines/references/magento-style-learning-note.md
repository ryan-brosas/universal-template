# Adobe Commerce / Magento coding standards — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `magento-style-*.md` capsules, `magento-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Coding standards overview](https://developer.adobe.com/commerce/php/coding-standards/) (primary index) | PHPCS `Magento2` standard; PHP/JS/LESS/jQuery/DocBlock guides |
| [PHP coding standard](https://developer.adobe.com/commerce/php/coding-standards/php) (primary) | PSR-1/12; insecure functions; unescaped output; `ClassName::class` rule |
| [Technical guidelines](https://developer.adobe.com/commerce/php/coding-standards/technical-guidelines) (primary) | strict_types; SOLID; DI; layers; service contracts; security; exceptions |
| [DocBlock standard](https://developer.adobe.com/commerce/php/coding-standards/docblock) (primary) | phpDocumentor-style; file headers; short/long descriptions |
| [Extension coding best practices](https://developer.adobe.com/commerce/php/best-practices/extensions) (secondary) | PSR-2/4 + Zend; composition over inheritance; PHPCS |
| [magento/magento-coding-standard](https://github.com/magento/magento-coding-standard) ruleset (verify) | Severity-10: superglobals, XSS, insecure functions, PSR closing tag |
| `php-coding-practices` (secondary) | PSR-12 baseline — Magento adds Magento2 sniffs + architectural rules |
| `webappsec-coding-practices` (secondary) | XSS/CSRF depth — Magento §15 maps sanitize/escape + CSRF tokens |

**Scope:** **Adobe Commerce / Magento Open Source extensions and customizations** — modules under `app/code/Vendor/Module`. **Not:** generic Symfony/Laravel PHP (`php-coding-practices`), WordPress/Drupal CMS skills, or full Magento platform architecture (use Magento foundation when present).

## Mental model

Magento style = **PSR mechanical compliance + Magento2 PHPCS security sniffs + architectural technical guidelines**:

1. **PHP & types** — PSR-1/12; `declare(strict_types=1)` on new files; explicit return types; scalar type hints; `ClassName::class` not string literals; no closing `?>` in `.php`.
2. **Class design & DI** — composition over inheritance; constructors only assign/validate deps; factories over bare `new`; generic interface type hints; modular `etc/di.xml`; stateless plugins.
3. **Security & exceptions** — prepared SQL; sanitize input / escape output; no superglobals in module code; forbidden insecure functions; layered `LocalizedException`; no swallowing exceptions.
4. **Layers & verify** — CQRS-ish layers; service contracts in `*Api` modules; PHPCS `--standard=Magento2`; PHPStan/PHPMD where configured; ESLint from magento-coding-standard.

## Decision tables

### PHP mechanical (Magento Coding Standard)

| Topic | Rule |
|---|---|
| Base | PSR-1 + PSR-12 compliance via PHPCS `Magento2` |
| strict_types | **MUST** on all new PHP files |
| Return types | **MUST** declare explicit return types on functions |
| Scalar hints | **SHOULD** type-hint scalar parameters |
| Class resolution | use `Foo::class` / `\Magento\Path\Class::class` — never string class names |
| Superglobals | `$_GET`, `$_POST`, `$_SERVER`, etc. forbidden in module code (use request object) |
| Output | no unescaped output in PHP (`.phtml` uses Magento escape helpers) |
| Insecure funcs | no `eval`, `exec`, `shell_exec`, etc. per ruleset |
| Closing tag | no `?>` at end of PHP class files (PSR-2) |

### Class design & DI (technical guidelines §2–4)

| Topic | Rule |
|---|---|
| SOLID | object decomposition MUST follow SOLID |
| Instantiation | object ready after construct — no public `init()`; factories over `new` (except DTOs) |
| Constructor | only dependency assignment + arg validation; no events in constructor |
| Dependencies | type-hint most generic interface needed; never request Proxy/Interceptor in ctor |
| Inheritance | SHOULD NOT inherit for reuse — prefer composition |
| Properties | non-public SHOULD be private; no setters except DTOs; static methods SHOULD NOT |
| DI config | module `etc/di.xml`; presentation prefs in `etc/{area}/di.xml`; no circular deps |
| Plugins | stateless; no plugins on data objects; no in-module plugins; around-plugins sparingly |

### Service contracts & layers (§6)

| Topic | Rule |
|---|---|
| Layers | Presentation → Service Contracts → Data Access; no upward dependencies |
| API modules | interfaces in `Vendor_ModuleApi`; web APIs under `Api/` + `Api/Data/` |
| Interface shape | prefer single `execute()` method per service interface (repo exception) |
| Presentation | actions return `ResultInterface`; blocks don't assume controller; templates no `new` |
| Persistence | entities no persistence logic; one scope per operation |
| Storefront reads | prefer GraphQL over service contracts for read scenarios |

### Security & exceptions (§5, §15)

| Topic | Rule |
|---|---|
| SQL | prepared statements only |
| XSS | sanitize input; escape output per Magento XSS guidelines |
| CSRF | tokens; state-changing requests via POST |
| Auth | no default credentials; rate-limit failed logins |
| Exceptions | user-facing → symptom/details/solution; don't catch where thrown; `LocalizedException` for UI |
| Logging | log in catch block only; don't log credentials from PDO errors |

### Verification toolchain

| Tool | Use |
|---|---|
| PHPCS | `vendor/bin/phpcs --standard=Magento2 app/code/Vendor/Module` |
| PHPCBF | auto-fix where supported |
| ESLint | `vendor/magento/magento-coding-standard/eslint/.eslintrc-magento` |
| PHPMD | project ruleset under `dev/tests/static/.../phpmd/ruleset.xml` |
| DocBlocks | phpDocumentor-style per DocBlock standard |

## Anti-patterns

- New PHP file without `declare(strict_types=1);`
- String literal class name instead of `::class`
- Direct `$_SERVER` / `$_GET` access in extension code
- Unescaped echo in non-template PHP
- Public `init()` or heavy work in constructor
- Requesting `Proxy` or `Interceptor` in constructor type hints
- Deep inheritance hierarchies for code reuse
- Mutable state on service classes
- Raw SQL string interpolation
- Catching and swallowing exceptions without logging
- Throwing generic `\Exception` from controllers
- Plugin that changes subject object state
- Service contract interface with many unrelated methods
- Template `.phtml` instantiating objects
- PHPCS Magento2 errors on changed paths

## Skill trace

| Artifact | Role |
|---|---|
| `magento-style-php-types.md` | PSR, strict_types, ::class, PHPCS mechanical |
| `magento-style-class-di.md` | SOLID, constructors, DI, composition |
| `magento-style-security-exceptions.md` | SQL, XSS, superglobals, exception rules |
| `magento-style-layers-verify.md` | service contracts, layers, PHPCS/ESLint |
| `magento-coding-practices/SKILL.md` | Magento extension review workflow |

## Relation to sibling skills

| Magento standards | php-coding-practices | drupal/wordpress |
|---|---|---|
| PSR-12 + Magento2 sniffs | PSR-12 generic | CMS-specific layout |
| strict_types mandatory new files | recommended pattern | WP omit `?>`; Drupal optional strict |
| DI via di.xml | constructor DI general | hook/procedural patterns |
| Service contracts / Api modules | interface segregation | N/A |

Security depth: `webappsec-coding-practices` for OWASP mapping beyond Magento §15 checklist.
