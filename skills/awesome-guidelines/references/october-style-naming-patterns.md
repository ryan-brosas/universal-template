<!-- capsule-v2 -->
# Naming patterns — do vendor codes, tables, MVC artifacts, views, and events follow October conventions?

**Source:** Developer Guide §Developer standards and patterns. **Question:** Are marketplace-facing names consistent across namespace, DB, components, and templates?

## Naming seam
**Path/Symbol:** Plugin registration, migrations, components, views, events.
**Signature:** `Acme.Blog`; `acme_blog_posts`; `_partial.htm`; `ProductList`.
**Data Shape:** `Event::fire('blog.post.save', [$this, $post]);`.

### Decisive pattern
```php
// Plugin code: Acme.Blog
// Table: acme_blog_posts with is_published column
// Component: ProductList, CategoryDetails
// Partial: _product-card.htm
// Global event: blog.post.beforeSave
```

**Flow:** **vendor/author code** starts uppercase — no underscores/dashes (`Acme.Blog`, not `acme.blog`) → **DB tables** `{author}_{plugin}_*`; **boolean columns** prefixed **`is_`** to avoid model property clashes → columns extending other plugins prefixed **`{author}_{plugin}_`** or acronym → **backend controllers** plural (`Products`) → **models** singular (`Product`) → **components** use **`List`** / **`Details`** suffix or descriptive non-conflicting name → **views**: partials start **`_`**; controller/layout views do not; **`-`** substitutes space, **`_`** substitutes folder; **`.htm` only** → **HTML**: form **`name` snake_case**; **`id` camelCase or hyphen-case**; **`class` hyphen-case** → **events**: use **before/after** terms not `onSomething`; **global** events prefixed with plugin/module (`blog.post.end`); **local** events omit prefix; pass **calling object first** on global events.
**Invariant:** lowercase vendor code, unprefixed plugin table, partial without `_`, or ambiguous component name colliding with model fails naming review.
**Probe:** migration table list vs plugin code; components/ and views/ directory audit.

## Verdict
October marketplace naming matrix for vendor, persistence, MVC, views, and events. Learning note: `october-style-learning-note.md`.
