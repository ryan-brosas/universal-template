<!-- capsule-v2 -->
# Security and escaping — is output escaped late with the correct WordPress function per context?

**Source:** Escaping Data handbook + PHP standards cross-refs. **Question:** Does every echoed variable use context-matched escaping at output, not early storage?

## Output seam
**Path/Symbol:** Template/plugin echo paths — HTML, attrs, URLs, JS, kses HTML.
**Signature:** escape at echo; whole-attribute escape; esc_* / wp_kses_* matrix.
**Data Shape:** `echo esc_html( $title );`; `esc_attr( $prefix . '-box' . $id )`; `wp_kses_post( $content )`.

### Decisive pattern
```php
echo '<a href="' . esc_url( $url ) . '">' . esc_html( $text ) . '</a>';

<input type="text" name="<?php echo esc_attr( $field_name ); ?>" />

<div class="<?php echo esc_attr( $prefix . '-widget-' . $id ); ?>">
	<?php echo wp_kses_post( $partial_html ); ?>
</div>
```

**Flow:** **escape late** at output site — prefer `echo esc_html( $x )` over assigning `$x = esc_html( $x )` early → match function to **context**: `esc_html` body text; `esc_attr` attributes (escape **whole** concatenated attribute value once); `esc_url` href/src; `esc_js` / `wp_json_encode` inline JS; `esc_textarea` textarea bodies; `wp_kses_post` trusted post-like HTML; `wp_kses()` with allowlist for partial untrusted HTML → localized strings: **`esc_html_e()`**, **`esc_attr__()`**, etc. → if early escape unavoidable, suffix variable **`_escaped`**, **`_safe`**, or **`_clean`** → sanitize/validate on **input**; escape on **output** — see Data Validation handbook for input side.
**Invariant:** raw `echo $var` in HTML, `esc_attr` on URL, or piecemeal attribute escaping fails security review.
**Probe:** grep `echo \$` without `esc_`/`wp_kses`; PHPCS `WordPress.Security.EscapeOutput`.

## Verdict
Late, context-correct escaping with whole-attribute discipline and kses for HTML fragments. Learning note: `wordpress-style-learning-note.md`.
