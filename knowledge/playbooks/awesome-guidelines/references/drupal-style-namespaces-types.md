<!-- capsule-v2 -->
# Namespaces and types — are classes PSR-4 under src/ with use imports and type hints?

**Source:** Drupal namespaces + PHP type-hint sections. **Question:** Does OOP code follow Drupal\module_name PSR-4 layout and typed APIs?

## OOP seam
**Path/Symbol:** `module_name/src/**/*.php` — services, plugins, entities.
**Signature:** `Drupal\module_name\Foo\Bar`; one class per file; typed methods.
**Data Shape:** `namespace Drupal\example\Plugin\Block;`; `public function build(): array`.

### Decisive pattern
```php
<?php

namespace Drupal\example\Plugin\Block;

use Drupal\Core\Block\BlockBase;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides an example block.
 */
final class ExampleBlock extends BlockBase implements ContainerFactoryPluginInterface {

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition): static {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
    );
  }

  /**
   * {@inheritdoc}
   */
  public function build(): array {
    return [
      '#markup' => $this->t('Example'),
    ];
  }

}
```

**Flow:** namespace **`Drupal\module_name\...`** mirrors **`module_name/src/...`** path — **`/src/` omitted** from namespace → **one class/interface/trait/enum per file**; filename matches class (`ExampleBlock.php`) → namespaced classes imported with **`use`** (no leading `\` on import); **global classes** use leading `\` (`new \DateTime()`) — do not `use` globals → **one class per use statement** → new methods: **parameter + return type hints**; prefer **interface** type hints over concrete classes; **`void`** when no return → suffixes: **`Interface`**, **`Trait`**, **`Test`** on appropriate types; no **"Drupal"** in class names; no **`Class`** in class names → **`declare(strict_types=1);`** on own line after file docblock when file is strict.
**Invariant:** class in `.module` without namespace when it has a superclass, missing type hints on new public API, or wrong PSR-4 path fails namespace review.
**Probe:** PSR-4 autoload map; PHPStan level on touched namespaces.

## Verdict
PSR-4 Drupal namespaces, import hygiene, and typed method signatures on new code. Learning note: `drupal-style-learning-note.md`.
