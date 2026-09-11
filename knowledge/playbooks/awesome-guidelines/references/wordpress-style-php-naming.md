<!-- capsule-v2 -->
# PHP naming and layout — does WordPress PHP follow snake_case, Yoda, tabs, and file conventions?

**Source:** WordPress PHP Coding Standards §General–Control Structures. **Question:** Are naming, mixed PHP/HTML tags, Yoda comparisons, and class file paths WordPress-compliant?

## PHP seam
**Path/Symbol:** Theme/plugin PHP — hooks, classes, templates.
**Signature:** snake_case functions; `Class_Name`; `class-class-name.php`; Yoda literals; tabs.
**Data Shape:** `function my_plugin_init()`; `class My_Plugin_Admin {}`; `'publish' === $status`.

### Decisive pattern
```php
<?php
/**
 * Plugin bootstrap.
 *
 * @package My_Plugin
 */

defined( 'ABSPATH' ) || exit;

function my_plugin_register_post_type() {
	if ( true === $enabled ) {
		do_action( "{$new_status}_{$post->post_type}", $post->ID, $post );
	}
}
```

**Flow:** **full PHP tags** only — no `<?` or `<?=` → multiline embedded PHP: open/close tags on **own lines** → **snake_case** for functions, variables, hooks, filters → **Class_Name** for classes/traits/interfaces/enums; **ALL_CAPS** constants → files: **lowercase-hyphens.php**; class file **`class-my-class-name.php`** from `My_Class_Name` → **tabs** indent; space after commas and around operators (except string concat `.`) → **Yoda** for literal/constant compares: `'foo' === $var` not `$var === 'foo'` → use **`elseif`**, not **`else if`** → ternary tests **true** branch; **no short ternary** → **`include $file;`** without extra parentheses → dynamic hooks: **`"{$var}_suffix"`** with braced vars, not concatenation in tag string.
**Invariant:** camelCase PHP identifiers, non-Yoda literal compare, shorthand tags, or misnamed class file fails WPCS naming review.
**Probe:** PHPCS `WordPress.NamingConventions`; grep `function [a-z]+[A-Z]` in changed PHP.

## Verdict
WordPress snake_case naming, class file mapping, Yoda compares, tab layout, and hook interpolation. Learning note: `wordpress-style-learning-note.md`.
