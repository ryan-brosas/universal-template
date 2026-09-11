<!-- capsule-v2 -->
# PHP types and PSR — does Magento PHP use strict_types, return types, PSR-12, and ::class resolution?

**Source:** PHP coding standard + technical guidelines §1 + Magento2 ruleset PSR refs. **Question:** Are new PHP files strictly typed, PSR-compliant, and free of string class literals?

## PHP seam
**Path/Symbol:** `app/code/Vendor/Module/**/*.php` — services, models, controllers.
**Signature:** `declare(strict_types=1);`; return types; `ClassName::class`.
**Data Shape:** `public function execute(string $sku): bool`; `$this->get(ProductRepositoryInterface::class)`.

### Decisive pattern
```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Model;

use Magento\Catalog\Api\ProductRepositoryInterface;

class ProductChecker
{
    public function __construct(
        private readonly ProductRepositoryInterface $productRepository,
    ) {
    }

    public function exists(string $sku): bool
    {
        try {
            $this->productRepository->get($sku);
            return true;
        } catch (\Magento\Framework\Exception\NoSuchEntityException) {
            return false;
        }
    }
}
```

**Flow:** all **new PHP files MUST** start with **`declare(strict_types=1);`** after opening tag → **explicit return types MUST** on functions/methods → **scalar parameter type hints SHOULD** be used → comply with **PSR-1** and **PSR-12** (enforced by PHPCS **`Magento2`**) → resolve classes with **`ClassName::class`** or **`\Fqcn\Class::class`** — never string literals for DI/type lookups → **no closing `?>`** in `.php` class files → run **`vendor/bin/phpcs --standard=Magento2`** on changed paths; **`phpcbf`** for auto-fixes where supported.
**Invariant:** missing strict_types on new file, absent return type, or `'Magento\Foo\Bar'` string class reference fails Magento PHP mechanical review.
**Probe:** PHPCS Magento2 on diff; grep `'\\\\Magento\\\\'` string class patterns.

## Verdict
Strict Magento PHP with PSR layout, typed signatures, and ::class resolution verified by PHPCS Magento2. Learning note: `magento-style-learning-note.md`.
