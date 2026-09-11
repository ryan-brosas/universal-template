<!-- capsule-v2 -->
# Documentation and i18n — are docblocks, hook summaries, and t() present on public API?

**Source:** Drupal API documentation standards + PHP coding i18n patterns. **Question:** Is every file/class/method documented and are user-visible strings translatable?

## Doc seam
**Path/Symbol:** DocBlocks on files, classes, hooks, services.
**Signature:** `/** @file */`; `@param` with `\Fqcn`; `Implements hook_*()`; `t()`.
**Data Shape:** summary ≤80 chars + period; `{@inheritdoc}` on identical overrides.

### Decisive pattern
```php
/**
 * @file
 * Batch API integration for example module.
 */

/**
 * Processes batch operation sets.
 *
 * @param array $items
 *   Item IDs to process.
 * @param array $context
 *   Batch context array passed by reference.
 */
function example_batch_process(array $items, array &$context): void {
  foreach ($items as $item) {
    $context['message'] = t('Processing @id', ['@id' => $item]);
  }
}

/**
 * Implements hook_help().
 */
function example_help() {
  return t('Example module help.');
}
```

**Flow:** every **file**, **class**, **method** (incl. private), and **constant** gets a **`/** */` docblock** → summary **≤80 chars**, starts capital, ends **period** → class/method summaries third-person (**Provides…**, **Returns…**) → **`@param`/`@return`/`@var`** use [PHPDoc types](https://phpstan.org/writing-php-code/phpdoc-types): `int`, `bool`, `array`; namespaced types with leading **`\`** → hook implementations: short summary **`Implements hook_foo().`** — omit param/return when standard → identical override: **`{@inheritdoc}`** only → user-visible strings via **`t()`**, **`$this->t()`**, or **`@Translation`** — **US English** spelling in source → wrap doc lines near **80 chars**; indent tag descriptions **2 spaces** → document **@throws** for thrown exceptions.
**Invariant:** undocumentated public method, hook with full @param block, or raw English UI string fails documentation/i18n review.
**Probe:** PHPCS Drupal comment sniffs; grep new strings missing `t(` in UI paths.

## Verdict
Complete docblocks, concise hook summaries, and translatable user strings. Learning note: `drupal-style-learning-note.md`.
