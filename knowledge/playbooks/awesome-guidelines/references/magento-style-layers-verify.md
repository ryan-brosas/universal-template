<!-- capsule-v2 -->
# Layers and verify — do service contracts, CQRS layers, docblocks, and CI gates hold?

**Source:** Technical guidelines §6–7 + DocBlock standard + coding standards index. **Question:** Are modules layered correctly with Api contracts and verified by PHPCS/ESLint?

## Layer seam
**Path/Symbol:** `*Api` modules, controllers, blocks, `.phtml`, static tests.
**Signature:** `Vendor_ModuleApi`; single-purpose interfaces; PHPCS Magento2.
**Data Shape:** `Api/Data/*Interface.php`; action returns `ResultInterface`; file `@api` docblock.

### Decisive pattern
```xml
<!-- Vendor/ModuleApi/etc/module.xml + Api interfaces -->
<!-- Vendor/Module/etc/di.xml maps implementation -->
```

```php
<?php
declare(strict_types=1);

namespace Vendor\ModuleApi\Api;

interface NotifyCustomerInterface
{
    /**
     * Send notification for order IDs.
     *
     * @param int[] $orderIds
     * @return void
     */
    public function execute(array $orderIds): void;
}
```

**Flow:** structure **Presentation → Service Contracts → Data Access** — layers MUST NOT depend upward → expose extension APIs in **`Vendor_ModuleApi`** module; web service interfaces under **`Api/`** + data interfaces under **`Api/Data/`** → prefer **single `execute()`** method per service interface (repository CRUD exception) → **storefront reads** SHOULD use **GraphQL** over new service contracts → presentation: actions return **`ResultInterface`**; blocks don't assume controller; **templates must not instantiate objects** → entities carry **no persistence logic** → **DocBlocks** per phpDocumentor standard — file header with short (+ optional long) description → verify: **`vendor/bin/phpcs --standard=Magento2 app/code/Vendor/Module`** → **ESLint** with **`vendor/magento/magento-coding-standard/eslint/.eslintrc-magento`** on JS → **PHPMD** ruleset when project configures static tests → fix **by rule across codebase**, not arbitrary one-off style drift.
**Invariant:** business logic in `.phtml`, fat multi-method service interface, or PHPCS Magento2 failure on changed extension paths fails layer/verify gate.
**Probe:** phpcs Magento2 exit 0 on diff; Api module boundary check on new public methods.

## Verdict
Layered Magento modules with Api contracts, docblocks, and PHPCS/ESLint static verification. Learning note: `magento-style-learning-note.md`.
