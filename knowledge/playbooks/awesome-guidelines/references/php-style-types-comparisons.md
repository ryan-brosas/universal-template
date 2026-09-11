<!-- capsule-v2 -->
# Types and comparisons — is modern PHP strictness enforced?

**Source:** PSR-12 §2.5, §4.6–§4.7; Clean Code PHP comparison/defaults. **Question:** Will strict mode and identical comparison prevent silent coercion bugs?

## Strict types seam
**Path/Symbol:** application `src/**/*.php` (non-generated).
**Signature:** `declare(strict_types=1);` immediately after opening tag.
**Data Shape:** short type keywords; declared return types on public methods.

### Decisive pattern
```php
<?php

declare(strict_types=1);

namespace Vendor\Package;

final class Pricing
{
    public function unitPrice(int $quantity, float $rate): float
    {
        return $quantity * $rate;
    }

    public function label(?string $name): string
    {
        return $name ?? 'default';
    }
}
```

**Flow:** enable strict types on new modules → use `bool`/`int`/`float`/`string`/`array`/`void`/`never` → nullable `?Type` when null is domain-valid → union types for PHP 8+ when needed.
**Invariant:** reserved keywords and built-in types lowercase; no `integer`/`boolean` aliases in new code.
**Probe:** grep `declare(strict_types=1)` in changed application files; PHPStan/Psalm level matches project baseline.

## Comparison seam
```php
$a = '42';
$b = 42;

if ($a !== $b) {
    // types differ — intentional
}

$port = $config['port'] ?? 8080;
$name = $_GET['name'] ?? $_POST['name'] ?? 'guest';
```

**Flow:** default to `===`/`!==` → use `??` for null/absent keys → document any intentional loose compare (`==`) with comment.
**Invariant:** loose equality in business logic without comment is a review reject.
**Probe:** static analyzer flags loose compares; no nested `isset() ? … : …` chains where `??` suffices.

## Parameter defaults seam
```php
// Good — typed default
function createBrewery(string $name = 'Hipster Brew Co.'): void
{
}

// Bad — null default then coalesce
function createBrewery($name = null): void
{
    $name = $name ?: 'Hipster Brew Co.';
}
```

**Flow:** type-hint parameters → supply defaults in signature → avoid `$x = null` + body coalesce when a string/int default suffices.
**Invariant:** public API parameters have types; nullable only when null carries meaning.
**Probe:** PHPStan reports no missing parameter types on public methods in diff.

## Verdict
Enable strict_types, identical comparison, typed defaults, and declared returns. Learning note: `php-style-learning-note.md`.
