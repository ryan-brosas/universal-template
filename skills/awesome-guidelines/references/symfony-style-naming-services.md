<!-- capsule-v2 -->
# Naming and services — do identifiers and DI service ids match Symfony conventions?

**Source:** Symfony coding standards §Naming Conventions, §Service Naming Conventions. **Question:** Are PHP, config, Twig, and service names in the correct case and suffix pattern?

## Naming seam
**Path/Symbol:** PHP types, parameters, Twig templates, service container ids.
**Signature:** camelCase code; snake_case config/Twig; FQCN primary service.
**Data Shape:** AbstractFoo, FooInterface, FooException; #[AsCommand]; framework.csrf_protection.

### Decisive pattern
```yaml
# services.yaml — main service id = FQCN
App\EventSubscriber\UserSubscriber: ~

parameters:
  app.http_status_code: 200
```

```php
abstract class AbstractWorker { }
interface CacheInterface { }
enum InputArgumentMode { case IsArray; }
```

**Flow:** **camelCase** vars/methods/args → **snake_case** config params, **route names**, **Twig variables** → **SCREAMING_SNAKE_CASE** constants → **UpperCamelCase** enum cases, classes, namespaces, **PHP filenames** → prefix **Abstract** (not PHPUnit *TestCase) → suffix **Interface**, **Trait**, **Exception** → service config attributes **`As*`**; controller arg attributes **`Map*`** → **snake_case** Twig templates (`section_layout.html.twig`) and web assets → PHPDoc types: **`bool`/`int`/`float`** not boolean/integer/double.
**Invariant:** camelCase route name, missing Interface suffix, or mis-cased Twig file fails naming review.
**Probe:** grep route names; list templates; service id vs class FQCN in services.yaml.

## Service seam
**Flow:** default service name = **FQCN** of class → multiple implementations: **FQCN** for primary; **lowercase_underscored** dotted ids for alternates (`something.service_name`) → parameter names **lowercase** (except `%env(VAR)%`) → add **class alias** for public services.
**Invariant:** primary autowired service with non-FQCN id without documented alias pattern fails service naming review.
**Probe:** bin/console debug:container for changed services.

## Verdict
Case matrix for code vs config/Twig plus FQCN-first service naming. Learning note: `symfony-style-learning-note.md`.
