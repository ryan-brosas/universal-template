<!-- capsule-v2 -->
# Files and namespaces — does autoload shape match PSR-1/PSR-4?

**Source:** PSR-1 §2–§3; PSR-4 autoloading. **Question:** Can Composer autoload every class without side effects on include?

## File hygiene seam
**Path/Symbol:** PSR-4 mapped `src/**/*.php`.
**Signature:** `<?php` opening only; UTF-8 without BOM.
**Data Shape:** one primary class/trait/interface per file; filename matches class name.

### Side-effect rule
```php
<?php

declare(strict_types=1);

namespace Vendor\Package;

final class OrderRepository
{
    // declarations only — no echo, ini_set, or global mutation at load time
}
```

**Bad (mixed):**
```php
<?php
ini_set('display_errors', '1');
echo '<html>';

class Foo {}
```

**Flow:** autoloaded files declare symbols only → bootstrap/front controller owns side effects → conditional function declarations are allowed (PSR-1 exception).
**Invariant:** PSR-4 class files MUST NOT emit output or mutate globals merely from being required.
**Probe:** `composer dump-autoload -o` succeeds; including class file in isolation produces no output; no `?>` closing tag.

## Namespace seam
```php
<?php

declare(strict_types=1);

namespace Acme\Billing;

use Acme\Billing\Model\Invoice;

final class InvoiceService
{
}
```

**Flow:** vendor-level namespace (`Acme\…`) → path `src/Billing/InvoiceService.php` under PSR-4 prefix → class name PascalCase (`InvoiceService`).
**Invariant:** class name StudlyCaps; method names `camelCase()`; class constants `UPPER_SNAKE_CASE`.
**Probe:** class FQCN matches composer.json PSR-4 mapping; grep shows no legacy `Vendor_Class_Name` in new code.

## Naming seam

| Element | Convention | Example |
|---|---|---|
| Class | PascalCase | `HttpClient` |
| Method | camelCase | `sendRequest()` |
| Class constant | UPPER_SNAKE | `MAX_RETRIES` |
| Property | project-consistent | `$invoiceId` (camelCase typical) |

**Flow:** pick property convention per package and apply consistently (PSR-1 defers property style).
**Invariant:** method names never `snake_case`; constants never camelCase.
**Probe:** PHPCS PSR-1 naming sniffs; review shows one property style per package.

## Verdict
Keep PSR-4 files side-effect-free with PascalCase types and camelCase methods. Learning note: `php-style-learning-note.md`.
