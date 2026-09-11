<!-- capsule-v2 -->
# Verify — does the codebase pass PHP CS Fixer and PSR Symfony baseline?

**Source:** Symfony coding standards intro; PHP CS Fixer. **Question:** Is contributed code mechanically aligned with Symfony's PSR-based ruleset?

## Verify seam
**Path/Symbol:** Symfony project or bundle repo root.
**Signature:** php-cs-fixer fix -v clean; PSR-1/2/4/12 baseline.
**Data Shape:** .php-cs-fixer.dist.php or Symfony rule set.

### Decisive pattern
```bash
cd your-project/
php php-cs-fixer.phar fix -v --dry-run --diff
# or: vendor/bin/php-cs-fixer fix -v
```

**Flow:** base rules on **PSR-1, PSR-2, PSR-4, PSR-12** → run **PHP CS Fixer** locally before PR — Symfony CI will auto-suggest fixes → pair with **`php-coding-practices`** (strict_types, PSR-4 side effects) on app code → optional **phpstan/psalm** for PHPDoc generics → on patch: structure + naming + PHPDoc capsules spot-check where fixer silent.
**Invariant:** Symfony contribution with fixer diff on changed PHP fails verify gate.
**Probe:** php-cs-fixer dry-run exit 0; CI style job green.

## Capsule cross-check
**Flow:** changed PHP → **structure-control** (Yoda, else) → **naming-services** (FQCN ids) → **phpdoc-exceptions** (license, throws) → fixer → unit tests (`bin/phpunit` / `php bin/phpunit`).
**Probe:** pre-commit or CI matrix includes cs-fix + tests.

## Verdict
PHP CS Fixer clean on changed paths plus capsule probes for Symfony-specific rules fixer may not cover. Learning note: `symfony-style-learning-note.md`.
