<!-- capsule-v2 -->
# Assets and verify — do HTML/CSS/JS match WordPress handbooks and PHPCS pass?

**Source:** WordPress HTML/CSS/JS standards + WPCS tooling + WCAG AA commitment. **Question:** Are front-end assets WordPress-shaped and mechanically verified?

## Asset seam
**Path/Symbol:** Theme templates, admin CSS/JS, block editor scripts.
**Signature:** quoted HTML attrs; kebab CSS selectors; camelCase JS; PHPCS WPCS.
**Data Shape:** `<input type="text" name="email" disabled />`; `.comment-form { }`; `const postId = 1;`.

### Decisive pattern
```html
<?php if ( ! have_posts() ) : ?>
<div id="post-not-found" class="post-not-found">
	<h1 class="entry-title"><?php esc_html_e( 'Not Found', 'my-theme' ); ?></h1>
	<?php get_search_form(); ?>
</div>
<?php endif; ?>
```

```css
#comment-form {
	background: #fff;
	margin: 1em 0;
}

input[type="text"] {
	line-height: 1.1;
}
```

```javascript
const userId = 1;

if ( 'publish' === postStatus ) {
	updatePost( userId );
}
```

**Flow:** **HTML** — lowercase tags/attrs; **always quote** attribute values; boolean attrs omit `="true"`; **tabs** indent aligned with surrounding PHP blocks → **CSS** — **kebab-case** selectors; `#fff` lowercase hex; double quotes in attribute selectors; avoid **over-qualified** selectors (`div.foo` → `.foo`) → **JS** — **camelCase** vars/functions (differs from PHP snake_case); **UpperCamelCase** classes/`@wordpress/element` components; **`const`/`let`** not `var` in new code; **`===`** strict equality; semicolons → **verify**: **`phpcs --standard=WordPress`** (or project ruleset extending WPCS) on changed PHP; ESLint/JSHint for JS where configured → **accessibility**: new/updated UI targets **WCAG 2.x AA** — pair with `wcag-accessibility-practices` for review depth.
**Invariant:** unquoted HTML attrs, camelCase CSS selectors, or PHPCS P0 violations on changed PHP fail asset/verify gate.
**Probe:** `vendor/bin/phpcs --standard=WordPress path/to/changed.php`; spot-check template quote discipline.

## Verdict
WordPress HTML/CSS/JS conventions plus PHPCS and WCAG-aware verification. Learning note: `wordpress-style-learning-note.md`.
