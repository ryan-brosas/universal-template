<!-- capsule-v2 -->
# Naming and files — do identifiers and paths match Kotlin conventions?

**Source:** Kotlin coding conventions §Source code organization, §Naming; Android §Naming. **Question:** Are packages, files, and constants autoload-friendly and consistent?

## Package and file seam
**Path/Symbol:** `src/**/**/*.kt`.
**Signature:** lowercase packages; PascalCase type files; no wildcard imports.
**Data Shape:** single primary type per file when feasible.

### Decisive pattern
```kotlin
package com.example.billing

import com.example.billing.model.Invoice
import com.example.billing.model.InvoiceId

class InvoiceProcessor(
    private val repository: InvoiceRepository,
) {
    companion object {
        const val MAX_BATCH = 100
    }
}
```

**File:** `src/billing/InvoiceProcessor.kt` (pure Kotlin tree drops common root package segment).

**Flow:** package lowercase no underscores → file name matches public type or descriptive PascalCase for multi-decl files → explicit imports only.
**Invariant:** `import com.example.billing.*` and `StringUtils.kt` / `Util.kt` names fail review.
**Probe:** ktlint `no-wildcard-imports`; filename matches primary `class`/`interface` in file.

## Naming seam

| Element | Rule | Example |
|---|---|---|
| Type | PascalCase | `HttpInputStream` |
| Function/property | camelCase | `processInvoice()` |
| Constant | SCREAMING_SNAKE | `MAX_BATCH` |
| Factory fn | may match type | `fun Invoice(): Invoice` |
| Backing prop | `_foo` / `foo` | see below |

```kotlin
class Cache {
    private val _items = mutableListOf<Item>()

    val items: List<Item>
        get() = _items
}
```

**Flow:** acronym rules — 2-letter all caps (`IOStream`); longer capitalize first letter only (`XmlParser`) → backing property underscore prefix for exposed read-only view.
**Invariant:** `process_invoice`, `XMLParser`, mutable `var` named like constant fail review.
**Probe:** naming inspection / ktlint standard naming rules on diff.

## Test naming (exception)
```kotlin
@Test
fun `returns empty list when id missing`() { /* ... */ }
```

**Flow:** backtick spaced names allowed **in tests only** (mind Android API 30+ for runtime).
**Invariant:** production code must not use backtick method names.
**Probe:** grep backtick defs outside `*Test.kt` / `test/` trees.

## Verdict
Lowercase packages, PascalCase files/types, camelCase members, explicit imports. Learning note: `kotlin-style-learning-note.md`.
