<!-- capsule-v2 -->
# PHP layout and naming — does Drupal PHP use 2-space indent, module prefixes, and consistent casing?

**Source:** Drupal PHP coding standards §Indenting–Naming. **Question:** Are layout, function prefixes, variable casing, and control structures Drupal-compliant?

## PHP seam
**Path/Symbol:** `.module`, `.install`, `.php` in modules/themes.
**Signature:** 2 spaces; `my_module_help()`; UpperCamelCase classes; braces always.
**Data Shape:** `$form['title'] = ['#type' => 'textfield'];`; `elseif`; no closing `?>`.

### Decisive pattern
```php
<?php

/**
 * @file
 * Example module hooks.
 */

use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Implements hook_help().
 */
function example_help(RouteMatchInterface $route_match) {
  if ('help.page' === $route_match->getRouteName()) {
    return t('Help text.');
  }
  return NULL;
}
```

**Flow:** **2 spaces** indent — **never tabs** — target **80** char lines → procedural functions **`module_name_action()`** lowercase + underscores + **module prefix** → variables **lowerCamelCase OR snake_case** — **never mix** in one file → classes **UpperCamelCase**; methods/properties **lowerCamelCase**; constants **`MODULE_CONSTANT`** → short arrays **`[]`** with spaces after commas and around `=>`; **trailing comma** on multi-line arrays → control: **always braces**; **`elseif`** not `else if`; space after keyword before `(` → binary operators spaced; **`?:`** and **`??`** when readable → **full `<?php` tags**; **omit closing `?>`** in module/include files → Unix **LF** line endings; file ends with single newline; no trailing whitespace.
**Invariant:** tabs, unprefixed procedural functions, mixed variable casing, closing `?>`, or `else if` fail Drupal PHP layout review.
**Probe:** PHPCS Drupal sniffs on changed paths; EditorConfig 2-space check.

## Verdict
Two-space Drupal PHP layout with module-prefixed functions and consistent casing discipline. Learning note: `drupal-style-learning-note.md`.
