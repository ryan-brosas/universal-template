<!-- capsule-v2 -->
# Database and i18n — are queries prepared and user strings translatable with text domains?

**Source:** WordPress PHP §Database + inline i18n patterns. **Question:** Does SQL use `$wpdb->prepare`, prefer WP APIs, and wrap user-visible strings for translation?

## Data seam
**Path/Symbol:** `$wpdb` queries; admin/front strings; sprintf messages.
**Signature:** unquoted `%s`/`%d` placeholders; text domain in `__()`; translator comments.
**Data Shape:** `$wpdb->prepare( "UPDATE $wpdb->posts SET post_title = %s WHERE ID = %d", $title, $id )`.

### Decisive pattern
```php
$title = sanitize_text_field( wp_unslash( $_POST['title'] ?? '' ) );

$wpdb->query(
	$wpdb->prepare(
		"UPDATE {$wpdb->posts} SET post_title = %s WHERE ID = %d",
		$title,
		$post_id
	)
);

$message = sprintf(
	/* translators: %s: user display name */
	__( 'Hello, %s!', 'my-plugin' ),
	esc_html( $user_name )
);
```

**Flow:** prefer **WordPress API functions** over direct DB access when available → raw SQL only when necessary; use **`$wpdb->prepare()`** with **`%s`**, **`%d`**, **`%f`**, **`%i`** placeholders — **never quote placeholders** → capitalize SQL keywords (`UPDATE`, `WHERE`) → pass **unslashed then sanitized** input to DB layer; escape at output not in stored values → all user-visible strings via **`__()`**, **`_e()`**, **`esc_html__()`** with consistent **`textdomain`** → **`/* translators: ... */`** before sprintf format strings → multiline **`sprintf( __( ... ), ... )`** assign format to variable first when complex → **never `extract()`** on untrusted arrays.
**Invariant:** interpolated SQL variables, quoted prepare placeholders, or bare English echo strings fail DB/i18n review.
**Probe:** PHPCS `WordPress.DB.PreparedSQL`; grep `__\(` missing second textdomain arg on new strings.

## Verdict
Prepared queries, API-first data access, and gettext-ready user strings. Learning note: `wordpress-style-learning-note.md`.
