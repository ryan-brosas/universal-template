<!-- capsule-v2 -->
# Naming and files — do identifiers and paths match Ruby conventions?

**Source:** Ruby Style Guide §Naming Conventions; Airbnb §Naming. **Question:** Are names grep-friendly and files autoloadable one-class-per-file?

## Identifier seam
**Path/Symbol:** methods, ivars, locals, constants, classes.
**Signature:** English identifiers; snake_case vs CapitalCase vs SCREAMING_SNAKE.
**Data Shape:** one primary class/module per file named `snake_case.rb`.

### Decisive pattern
```ruby
module Billing
  class InvoiceProcessor
    MAX_LINE_ITEMS = 100

    def process(invoice)
      return false if invoice.empty?

      invoice.valid?
    end

    def save!(invoice)
      raise InvalidInvoice, 'missing total' unless invoice.total?

      repository.store(invoice)
    end
  end
end
```

**Flow:** class `CapitalCase` (acronyms uppercase: `HTTPClient`) → methods/vars `snake_case` → non-class constants `SCREAMING_SNAKE`.
**Invariant:** `someMethod`, `Some_Class`, `SomeConst = 5` fail review.
**Probe:** Naming cops (`Naming/MethodName`, `Naming/ConstantName`) clean; no camelCase methods in new code.

## Predicate and bang seam
```ruby
def empty?(collection)
  collection.count.zero?
end

def activate!
  raise AlreadyActive if active?

  self.active = true
end
```

**Flow:** boolean queries end with `?` without `is_`/`does_` prefix → mutating/dangerous methods end with `!` only when non-bang alternative exists.
**Invariant:** `is_empty?` and lone `update!` without `update` are review rejects.
**Probe:** grep `def is_` in diff; every `!` method has matching safe method.

## File seam
```
lib/billing/invoice_processor.rb  →  Billing::InvoiceProcessor
spec/billing/invoice_processor_spec.rb
```

**Flow:** file path snake_case mirrors constant path → one class per file when feasible → directories snake_case.
**Invariant:** `InvoiceProcessor.rb` or multi-class files without reason fail review.
**Probe:** Zeitwerk/autoload eager load succeeds; filename matches primary constant.

## Verdict
Use snake_case files/methods, CapitalCase types, `?`/`!` suffix discipline. Learning note: `ruby-style-learning-note.md`.
