# WordPress coding standards — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `wordpress-style-*.md` capsules, `wordpress-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/) (primary index) | PHP/HTML/CSS/JS handbooks; WCAG AA commitment for new/updated code |
| [PHP Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/php/) (primary) | Naming, whitespace, Yoda, `$wpdb->prepare`, hooks, OOP, no `extract()` |
| [HTML Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/html/) (primary) | Lowercase tags/attrs, quoted attrs, tabs, PHP/HTML indent alignment |
| [CSS Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/css/) (primary) | kebab-case selectors, hex colors, property order, avoid over-qualification |
| [JavaScript Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/javascript/) (primary) | camelCase JS (differs from PHP snake_case), `const`/`let`, strict equality |
| [Escaping Data](https://developer.wordpress.org/apis/security/escaping/) (secondary) | Escape late at output; context-specific `esc_*` / `wp_kses_*` |
| `php-coding-practices` (secondary) | PSR layout baseline — WordPress uses tabs, snake_case, Yoda, no `strict_types` mandate |
| `wcag-accessibility-practices` (secondary) | WCAG AA target for WP core/themes/plugins |
| [WordPress Coding Standards tooling](https://github.com/WordPress/WordPress-Coding-Standards) (verify) | PHPCS `WordPress-Core` ruleset |

**Scope:** **Themes, plugins, and core-style PHP** in the WordPress ecosystem. **Not:** generic PSR Symfony/Laravel style (`php-coding-practices`), full plugin architecture (WordPress foundation docs), or third-party vendored libraries (explicitly exempt from WPCS).

## Mental model

WordPress style = **ecosystem interoperability + security/translatability**, not just aesthetics:

1. **PHP layout & naming** — tabs; snake_case functions/vars; `Class_Name` files as `class-class-name.php`; Yoda conditions; full `<?php ?>` tags; dynamic hooks via `"{$var}_suffix"`.
2. **Security at output** — escape late with the right function per context (`esc_html`, `esc_attr`, `esc_url`, `wp_kses_post`); sanitize on input; `$wpdb->prepare()` for SQL.
3. **Database & hooks** — prefer WP APIs over raw SQL; prepared placeholders unquoted; hook names lowercase with underscores; no `extract()`.
4. **Assets & verify** — HTML quoted attrs; CSS kebab selectors; JS camelCase; PHPCS WPCS in CI; WCAG AA for UI changes.

## Decision tables

### PHP — naming & files

| Topic | Rule |
|---|---|
| Functions, vars, hooks | lowercase + underscores (`some_function`, `$post_id`) |
| Classes, traits, interfaces, enums | `Capitalized_Words` (`Walker_Category`, `WP_Error`) |
| Constants | `ALL_CAPS` with underscores |
| Plugin/theme PHP files | lowercase, hyphen-separated (`my-plugin-name.php`) |
| Class files | `class-{hyphenated-class}.php` from class name |
| PHP in mixed templates | multiline `<?php`/`?>` on own lines; no shorthand tags |
| Dynamic hooks | `"{$new_status}_{$post->post_type}"` not concatenation |

### PHP — control & formatting

| Topic | Rule |
|---|---|
| Indent | tabs (4-space display width in PHPCS) |
| Comparisons | Yoda for `==`, `!=`, `===`, `!==` with literals/constants on left |
| Conditionals | `elseif` not `else if` |
| Ternary | test true branch; no short ternary `?:` |
| Arrays | short array syntax `[]`; trailing commas on multi-line |
| `@` operator | avoid error suppression |
| OOP | one class/trait/interface/enum per file; always declare visibility |
| Namespaces | unique vendor prefix; never `wp`/`WordPress` prefix |

### Security & i18n

| Context | Function |
|---|---|
| HTML body text | `esc_html()` / `esc_html__()` / `esc_html_e()` |
| HTML attribute | `esc_attr()` — escape whole concatenated attribute value |
| URL in href/src | `esc_url()` |
| Trusted post HTML | `wp_kses_post()` |
| Untrusted partial HTML | `wp_kses()` with allowlist |
| Inline JS | `esc_js()` or `wp_json_encode()` |
| Textarea | `esc_textarea()` |
| User strings | `__()`, `_e()`, `sprintf( __( '...', 'textdomain' ), ... )` with translator comments |
| SQL | `$wpdb->prepare( '... %s ... %d', $str, $id )` — placeholders never quoted |

### HTML / CSS / JS (when in WP tree)

| Layer | Rule |
|---|---|
| HTML | lowercase tags/attrs; always quote attribute values; tabs; boolean attrs without `="true"` |
| CSS | kebab-case selectors; `#fff` hex; double quotes in `[type="text"]`; avoid over-qualified selectors |
| JS | camelCase vars/functions; UpperCamelCase classes/components; `const`/`let`; `===`; semicolons |

## Anti-patterns

- camelCase PHP function or variable names
- Shorthand PHP tags `<?=` or `<?`
- `$var === 'literal'` instead of Yoda `'literal' === $var`
- Raw `$wpdb->query( "SELECT ... $var" )` without prepare
- Quoted `%s`/`%d` placeholders inside prepare string
- `echo $user_input` without context-appropriate escape at output
- Early escape stored in variable without `_escaped` suffix when late escape impossible
- `extract()` on request or query data
- `@` to silence errors instead of handling them
- `else if` instead of `elseif`
- Short ternary `?:`
- Unquoted HTML attributes (`name=email`)
- CSS `#commentForm` camelCase or `div.container` over-qualification
- JS snake_case variable names in admin/block scripts
- Missing text domain in `__()` / `_e()`
- Prefixing namespace with `wp` or `WordPress`

## Skill trace

| Artifact | Role |
|---|---|
| `wordpress-style-php-naming.md` | PHP naming, files, Yoda, hooks, layout |
| `wordpress-style-security-escape.md` | late escape, sanitize, kses matrix |
| `wordpress-style-database-i18n.md` | `$wpdb->prepare`, APIs over SQL, i18n |
| `wordpress-style-assets-verify.md` | HTML/CSS/JS + PHPCS + a11y |
| `wordpress-coding-practices/SKILL.md` | WordPress review workflow |

## Relation to sibling skills

| WordPress standards | php-coding-practices |
|---|---|
| snake_case, Yoda | camelCase PSR, identical `===` without Yoda mandate |
| tabs | 4 spaces PSR-12 |
| `class-wp-error.php` | PSR-4 `WP_Error.php` |
| PHPCS WordPress-Core | PHPCS PSR-12 / PHP-CS-Fixer |

Accessibility: `wcag-accessibility-practices` for WCAG AA UI work beyond style handbook quick guide.
