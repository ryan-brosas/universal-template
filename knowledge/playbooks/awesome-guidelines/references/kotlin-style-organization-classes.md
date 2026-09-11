<!-- capsule-v2 -->
# Organization and classes — is structure readable top-to-bottom?

**Source:** Kotlin coding conventions §Source code organization, §Class layout. **Question:** Can a reader follow class logic without jumping alphabetically?

## Directory seam
**Path/Symbol:** project source roots (`src/main/kotlin`, KMP source sets).
**Signature:** directory mirrors package; pure Kotlin drops shared root segment.
**Data Shape:** related declarations may share a file if semantically coupled and < few hundred lines.

### Pure Kotlin layout
```
src/
  billing/
    InvoiceProcessor.kt      # com.example.billing.InvoiceProcessor
    model/
      Invoice.kt             # com.example.billing.model.Invoice
```

**Flow:** map package → folder path → co-locate extensions with their type when all clients need them → client-specific extensions live with client code.
**Invariant:** dumping all extensions of a type into `FooExtensions.kt` without client scope fails review.
**Probe:** package statement matches folder path; `./gradlew compileKotlin` / IDE sync succeeds.

## Class layout seam
```kotlin
class OrderService(
    private val repository: OrderRepository,
) {
    private val cache = mutableMapOf<OrderId, Order>()

    init {
        require(repository.isReady())
    }

    constructor(repository: OrderRepository, warmCache: Boolean) : this(repository) {
        if (warmCache) preload()
    }

    fun find(id: OrderId): Order? = repository.find(id)

    fun find(id: OrderId, includeArchived: Boolean): Order? =
        if (includeArchived) repository.findAny(id) else find(id)

    companion object {
        fun create(): OrderService = OrderService(OrderRepository())
    }
}
```

**Flow:** properties/init → secondary constructors → methods (overload groups adjacent) → companion → nested types at use site or end if external.
**Invariant:** sorting methods alphabetically or splitting extension methods into distant blocks fails review.
**Probe:** review checklist: overloads adjacent; interface overrides follow interface member order.

## Interface implementation seam
```kotlin
interface Parser {
    fun parse(input: String): Result
    fun supports(mime: String): Boolean
}

class JsonParser : Parser {
    override fun parse(input: String): Result { /* ... */ }
    override fun supports(mime: String): Boolean { /* ... */ }

    private fun decode(input: String): JsonElement { /* ... */ }
}
```

**Flow:** override order mirrors interface declaration; private helpers interleaved only when aiding readability.
**Invariant:** random override order vs interface contract fails review on public API types.
**Probe:** side-by-side diff with interface shows matching order.

## Verdict
Package-aligned folders, semantic file grouping, property→ctor→method→companion class order. Learning note: `kotlin-style-learning-note.md`.
