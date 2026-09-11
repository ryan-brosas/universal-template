<!-- capsule-v2 -->
# Class design and DI — are objects composable, constructor-safe, and wired via di.xml?

**Source:** Technical guidelines §2–4 + extension composition guidance. **Question:** Does extension code favor composition, lean constructors, interface DI, and modular di.xml?

## DI seam
**Path/Symbol:** Module classes + `etc/di.xml`, `etc/frontend/di.xml`.
**Signature:** interface ctor hints; no Proxy in ctor; factories over new.
**Data Shape:** `etc/di.xml` preferences; stateless plugins; no inheritance reuse.

### Decisive pattern
```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Model;

use Vendor\Module\Api\RendererInterface;

class CompositeRenderer implements RendererInterface
{
    /**
     * @param RendererInterface[] $renderers
     */
    public function __construct(
        private readonly array $renderers,
    ) {
        foreach ($renderers as $renderer) {
            if (!$renderer instanceof RendererInterface) {
                throw new \InvalidArgumentException('RendererInterface expected.');
            }
        }
    }

    public function render(string $phrase): string
    {
        $result = '';
        foreach ($this->renderers as $renderer) {
            $result .= $renderer->render($phrase);
        }
        return $result;
    }
}
```

**Flow:** follow **SOLID** decomposition → **composition over inheritance** for reuse — avoid deep extends chains → object **ready after construct** — no public **`init()`** loaders → **constructor** only assigns dependencies and validates args — **no events in constructor** → depend on **most generic interface** type — never type-hint **Proxy** or **Interceptor** explicitly → prefer **factories** over bare **`new`** (DTOs/exceptions exempt) → **non-public SHOULD be private**; **no setters** except DTOs; **avoid static methods** → modular DI in **`module/etc/di.xml`**; presentation prefs in **`etc/{area}/di.xml`** — keep **`app/etc/di.xml`** framework-only → **plugins stateless**; no plugins on data objects; no in-module plugins; around-plugins only to substitute behavior → **no circular dependencies**.
**Invariant:** heavy constructor logic, RedisAdapter concrete ctor hint, or mutable service singleton state fails class/DI review.
**Probe:** di.xml diff review; PHPCS `Magento2.Classes.DiscouragedDependencies` on changed code.

## Verdict
Composable Magento classes with interface DI, lean constructors, and modular di.xml wiring. Learning note: `magento-style-learning-note.md`.
