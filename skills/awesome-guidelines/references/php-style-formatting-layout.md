<!-- capsule-v2 -->
# Formatting and layout — does code match PSR-12 mechanical rules?

**Source:** PSR-12 §2–§5, §7. **Question:** Will PHP-CS-Fixer, Laravel Pint, or PHPCS (PSR-12 ruleset) pass on changed files?

## Layout seam
**Path/Symbol:** `*.php` source files.
**Signature:** 4-space indent; Unix LF; no trailing whitespace; one statement per line.
**Data Shape:** soft 120 columns; prefer 80 when wrapping.

### Decisive pattern
```php
<?php

declare(strict_types=1);

namespace Vendor\Package;

use Vendor\Package\Bar;
use Vendor\Package\Baz;

class Foo
{
    public function process(int $a, ?int $b = null): array
    {
        if ($a === $b) {
            return [];
        }

        return $this->build($a, $b);
    }
}
```

**Flow:** `declare` → blank → `namespace` → blank → grouped `use` → blank → code → file ends with LF, no closing `?>`.
**Invariant:** tabs never used; pure PHP files omit closing tag; no more than one statement per line.
**Probe:** `vendor/bin/php-cs-fixer fix --dry-run` or Pint/PHPCS PSR-12 ruleset exit 0; `file` shows LF line endings.

## Control-structure seam
```php
if ($expr1 && $expr2) {
    doWork();
} elseif ($expr3) {
    alternate();
} else {
    fallback();
}

foreach ($items as $key => $value) {
    handle($key, $value);
}
```

**Flow:** space after keyword; brace on same line; `elseif`/`else`/`catch`/`finally` on prior closing brace line; multiline conditions break after operator.
**Invariant:** `else`/`catch`/`finally` never on its own line separated from closing `}`.
**Probe:** PHPCS `PSR12` sniffs clean on control structures in diff.

## Import seam
```php
use Vendor\Package\{ClassA as A, ClassB};

use function Vendor\Package\{functionA, functionB};

use const Vendor\Package\{CONSTANT_A, CONSTANT_B};
```

**Flow:** class imports → blank → function imports → blank → const imports; alphabetical within group; group imports allowed with trailing comma on multiline.
**Invariant:** import groups separated by exactly one blank line; no blank lines inside a group.
**Probe:** import-order fixer rule passes; no unused imports in changed files.

## Verdict
Adopt PSR-12 layout (4-space, LF, header order, brace rules). Learning note: `php-style-learning-note.md`.
