<!-- capsule-v2 -->
# Security and exceptions — are SQL prepared, output escaped, superglobals avoided, and exceptions layered?

**Source:** Technical guidelines §5 + §15 + Magento2 security sniffs. **Question:** Does extension code meet Magento security and exception handling rules?

## Security seam
**Path/Symbol:** DB access, templates, controllers, catch blocks.
**Signature:** prepared SQL; escape output; no $_GET; LocalizedException for UI.
**Data Shape:** `$connection->fetchOne($select, ['sku' => $sku])`; `$escaper->escapeHtml($value)`.

### Decisive pattern
```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Model;

use Magento\Framework\App\ResourceConnection;
use Magento\Framework\Exception\LocalizedException;

class SkuLookup
{
    public function __construct(
        private readonly ResourceConnection $resource,
    ) {
    }

    /**
     * @throws LocalizedException
     */
    public function findTitle(string $sku): string
    {
        $connection = $this->resource->getConnection();
        $select = $connection->select()
            ->from($this->resource->getTableName('catalog_product_entity'), ['sku'])
            ->where('sku = ?', $sku);

        $row = $connection->fetchRow($select);
        if (!$row) {
            throw new LocalizedException(__('Product with SKU %1 was not found.', $sku));
        }
        return (string) $row['sku'];
    }
}
```

**Flow:** **prepared statements** / query builder binds for SQL — never interpolate user input into SQL strings → **sanitize input; escape output** — follow Magento XSS guidelines in templates (`.phtml` escape helpers) → **no superglobals** (`$_GET`, `$_POST`, `$_SERVER`, …) in module code — use **Request** object in presentation layer → forbid **insecure functions** (`eval`, `shell_exec`, …) per ruleset → **CSRF tokens** for state-changing POST actions → **no default admin credentials** → catch/log exceptions — **do not swallow** without logging/workaround → don't catch in same function that throws — surface user errors via **`LocalizedException`** (symptom/details/solution pattern) — **don't throw generic `\Exception`** from controllers → wrap third-party calls in **try/catch** → **log only in catch** block that handles exception.
**Invariant:** raw SQL concat, unescaped PHP output, superglobal read, or absorbed exception fails Magento security review.
**Probe:** PHPCS `Magento2.Security.*` sniffs; grep `\$_(GET|POST|SERVER|REQUEST)` in `app/code`.

## Verdict
Prepared data access, escaped output, request abstraction, and disciplined exception handling. Learning note: `magento-style-learning-note.md`.
