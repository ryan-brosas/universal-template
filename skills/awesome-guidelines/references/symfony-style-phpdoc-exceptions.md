<!-- capsule-v2 -->
# PHPDoc, exceptions, and license — are docs sparse, errors formatted, and headers present?

**Source:** Symfony coding standards §Documentation, §Structure (exceptions), §License. **Question:** Do PHPDoc blocks add value, exception strings follow Symfony format, and files carry MIT headers?

## PHPDoc seam
**Path/Symbol:** Symfony PHP docblocks and throw sites.
**Signature:** multi-line blocks; grouped annotations; sprintf exceptions.
**Data Shape:** MIT license before namespace; capitalized error sentences with period.

### Decisive pattern
```php
/*
 * This file is part of the Symfony package.
 * ...
 */

/**
 * Transforms the input given as the first argument.
 *
 * @param array<string, mixed> $options an options collection
 *
 * @throws \RuntimeException when an invalid option is provided
 */
private function transformText(bool|string $dummy, array $options = []): ?string
```

```php
throw new \RuntimeException(sprintf('Unrecognized option "%s".', $name));
trigger_deprecation('symfony/package', '5.1', 'The %s() method is deprecated.', __METHOD__);
```

**Flow:** PHPDoc only when it adds info **beyond** name/native types/context → allowed extras: **generics**, **`@psalm-return`**, class constants, callable types → **group** annotations of same type; blank line between groups → **omit @return** on void → **no one-line** PHPDoc blocks (even `{@inheritdoc}`) → exceptions: concatenate with **sprintf** → messages use **double quotes** for technical names — **no backticks** → sentence **starts capital**, ends **`.`** → class names in errors: **`get_debug_type($x)`** not **`$x::class`** → **MIT license block** before **namespace** on every PHP file.
**Invariant:** backtick exception message, one-line class docblock, or missing license header on new Symfony-style file fails documentation review.
**Probe:** grep throw new messages; head -20 new PHP files for license; phpstan/psalm on annotated generics.

## Verdict
Sparse valuable PHPDoc, Symfony exception/deprecation prose, MIT header on all PHP files. Learning note: `symfony-style-learning-note.md`.
