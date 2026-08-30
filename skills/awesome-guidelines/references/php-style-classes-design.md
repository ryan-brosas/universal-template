<!-- capsule-v2 -->
# Classes and design — are objects testable and intentionally scoped?

**Source:** Clean Code PHP (visibility, final, DI, early return); PHP The Right Way (DI over singleton). **Question:** Can dependencies be swapped in tests without global state?

## Visibility seam
**Path/Symbol:** domain/service classes in `src/`.
**Signature:** minimal public surface; properties not public unless value object/DTO contract.
**Data Shape:** constructor-promoted dependencies when using PHP 8+.

### Decisive pattern
```php
<?php

declare(strict_types=1);

namespace Vendor\Billing;

final class InvoiceService
{
    public function __construct(
        private InvoiceRepository $repository,
        private ClockInterface $clock,
    ) {
    }

    public function createForAccount(AccountId $accountId): Invoice
    {
        if ($this->repository->hasOpenInvoice($accountId)) {
            throw new OpenInvoiceExists();
        }

        return $this->repository->save(
            Invoice::draft($accountId, $this->clock->now())
        );
    }
}
```

**Flow:** inject collaborators via constructor → keep methods one abstraction level → return early on guard conditions.
**Invariant:** domain services avoid `public $property` mutation; no hidden `global`/`$_SESSION` writes inside methods.
**Probe:** unit tests construct service with mocks — no `Singleton::getInstance()` required.

## Final & composition seam
```php
final class ReportExporter
{
    public function __construct(private CsvWriter $writer)
    {
    }

    public function export(array $rows): string
    {
        return $this->writer->write($rows);
    }
}
```

**Flow:** default `final class` → use composition/wrap over deep inheritance → extract interfaces at consumer when mocking needed.
**Invariant:** singleton `getInstance()` for domain services is a review reject — prefer DI container or explicit wiring (PHPTRW).
**Probe:** grep new code for `getInstance(` and `extends` depth; favor ≤1 level inheritance in application layer.

## Constants & magic values seam
```php
final class Permissions
{
    public const READ = 1;
    public const WRITE = 2;
    public const DELETE = 4;
}

if ($user->access & Permissions::WRITE) {
    allowEdit();
}
```

**Flow:** replace magic numbers with class constants or enums (PHP 8.1+) → name regex capture groups → limit function arity (≤3; use DTO when growing).
**Invariant:** unexplained numeric/string literals in business logic fail review.
**Probe:** no bare numeric flags in conditionals without named constant/enum nearby.

## Verdict
Prefer final, injected, early-return classes with private state and named constants. Learning note: `php-style-learning-note.md`.
