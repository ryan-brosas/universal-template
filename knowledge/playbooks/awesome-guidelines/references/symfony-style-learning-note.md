# Symfony coding standards — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `symfony-style-*.md` capsules, `symfony-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Symfony coding standards](https://symfony.com/doc/current/contributing/code/standards.html) (primary) | PSR-1/2/4/12 base; structure; Yoda; naming; services; PHPDoc; exceptions; PHP CS Fixer |
| symfony/symfony-docs `contributing/code/standards.rst` (primary mirror) | Full example class; service naming; license block |
| `php-coding-practices` (secondary) | PSR-12, strict_types — Symfony adds Yoda, service FQCN, Symfony PHPDoc rules |
| [PHP CS Fixer](https://cs.symfony.com/) (secondary verify) | Mechanical enforcement tool referenced by Symfony |

**Scope:** **Symfony-style PHP** (components, bundles, apps). **Twig/assets naming** included. **Not:** full Symfony architecture (`symfony` foundation if exists) or generic PHP without Symfony conventions.

## Mental model

Symfony style = **PSR mechanical layout + Symfony opinionated control flow and naming**:

1. **Structure** — spacing, Yoda conditions, identical `===`, no else after return, brace bodies, promoted constructor params.
2. **Naming** — camelCase PHP; snake_case config/routes/Twig; Abstract/Interface/Trait/Exception suffixes; As/Map attributes.
3. **Services & files** — service id = FQCN; MIT license header; UpperCamelCase PHP files; snake Twig.
4. **PHPDoc & errors** — sparse useful docs; sprintf exceptions; get_debug_type; PHP CS Fixer verify.

## Decision tables

### Tooling

| Topic | Rule |
|---|---|
| Fixer | PHP CS Fixer (`php-cs-fixer fix -v`) before PR |
| Base | PSR-1, PSR-2, PSR-4, PSR-12 |

### Structure & control flow

| Topic | Rule |
|---|---|
| Commas | Space after comma |
| Binary ops | Spaces around `==`, `&&`, etc.; **not** around `.` concat |
| Unary | Adjacent to variable |
| Comparison | Identical `===` unless juggling needed |
| Yoda | `'values' === $x` to prevent accidental assignment |
| Arrays | Trailing comma in multi-line arrays |
| return | Blank line before return unless sole statement in group |
| null/void | `return null;` vs bare `return;` for void |
| Tests | No `void` return type on test methods |
| Braces | Always for control bodies |
| Classes | One public class per file |
| Inheritance | extends/implements on same line as class |
| Order | properties → public → protected → private (ctor/setUp/tearDown first) |
| Args | Same line as method name except promoted ctor (one param per line + trailing comma) |
| new | Always parentheses `new Foo()` |
| else | No else/elseif/break after if/case that returns/throws |
| Offsets | No spaces around `[` `]` |
| use | import every non-global class |
| PHPDoc null | `null` last in union types |

### Exceptions & messages

| Topic | Rule |
|---|---|
| Concat | sprintf for exception strings |
| Quotes | Double quotes in messages; no backticks for symbols |
| Sentence | Capital start, trailing period |
| Class in msg | `get_debug_type($obj)` not `$obj::class` |

### Naming

| Topic | Rule |
|---|---|
| PHP vars/methods | camelCase |
| Config/routes/Twig vars | snake_case |
| Constants | SCREAMING_SNAKE_CASE |
| Enum cases | UpperCamelCase |
| Classes | UpperCamelCase namespaces |
| Abstract | `Abstract` prefix |
| Interface | `Interface` suffix |
| Trait | `Trait` suffix |
| Exception | `Exception` suffix |
| Attributes | `As*` service; `Map*` controller args |
| PHP files | UpperCamelCase.php |
| Twig/assets | snake_case |

### Services

| Topic | Rule |
|---|---|
| Main service | id = FQCN |
| Aliases | Multiple services: FQCN for main; snake_case dotted for others |
| Params | lowercase (except `%env(VAR)%`) |
| Public alias | Class alias to service id |

### Documentation & license

| Topic | Rule |
|---|---|
| PHPDoc | Only when adds info beyond name/types |
| Allowed extras | Generics, @psalm-return, class constants, callable types |
| Group | Same annotation types together |
| @return | Omit if void |
| Blocks | No one-line PHPDoc blocks |
| License | MIT block before namespace in every PHP file |

## Anti-patterns

- Manual style without PHP CS Fixer on Symfony contributions
- Loose `==` without justification
- `$foo === 'bar'` instead of Yoda when comparing to literal
- else after return in same if chain
- break after return in switch case
- Spaces around array offset brackets
- Missing `use` for namespaced class
- Backticks in exception messages
- Exception message without trailing period
- `$command::class` in user-facing exception text
- `AbstractFoo` missing on new abstract class
- Service id not FQCN for primary service
- camelCase Twig template name
- One-line `/** {@inheritdoc} */`
- Missing MIT license header in new Symfony-style file

## Skill trace

| Artifact | Role |
|---|---|
| `symfony-style-structure-control.md` | spacing, Yoda, flow, class order |
| `symfony-style-naming-services.md` | naming matrix, DI service ids |
| `symfony-style-phpdoc-exceptions.md` | PHPDoc, errors, license |
| `symfony-style-verify.md` | PHP CS Fixer, CI |
| `symfony-coding-practices/SKILL.md` | Symfony PHP review workflow |

## Relation to sibling skills

| Symfony standards | php-coding-practices |
|---|---|
| Yoda conditions | identical `===` general |
| Service FQCN ids | DI general |
| PHP CS Fixer ruleset | PHP-CS-Fixer/Pint generic |
| MIT header | not in generic PHP skill |

Framework patterns: Symfony foundation docs when present.
