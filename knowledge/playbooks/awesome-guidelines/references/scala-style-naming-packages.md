<!-- capsule-v2 -->
# Naming and packages — do identifiers follow Scala conventions?

**Source:** Scala style guide §Naming; Databricks §Naming. **Question:** Are packages, accessors, and nullary method parens idiomatic?

## Package and type seam
**Path/Symbol:** packages, classes, traits, objects.
**Signature:** reverse-DNS lowercase packages; UpperCamelCase types.
**Data Shape:** acronyms as words in names (`maxId`, `xHtml`).

### Decisive pattern
```scala
package com.example.billing

final case class Invoice(id: InvoiceId, total: BigDecimal)

object Invoice {
  val DefaultCurrency: String = "USD"
}

trait InvoiceRepository {
  def find(id: InvoiceId): Option[Invoice]
}
```

**Flow:** `package com.example.project` not single word `coolness` → types/objects UpperCamelCase → public names descriptive; short locals OK in tiny scopes.
**Invariant:** `package coolness` and `XHTML` acronym casing fail review.
**Probe:** package mirrors directory layout; public API names readable without types.

## Accessor/mutator seam
```scala
class Company {
  private var _name: String = ""

  def name: String = _name

  def name_=(value: String): Unit = {
    _name = value
  }
}
```

**Flow:** accessor named after property → mutator `prop_=` enables assignment syntax → avoid Java `getName`/`setName` in Scala API.
**Invariant:** public `setFoo`/`getFoo` pair in new Scala code fails review.
**Probe:** `foo.bar = x` works with `bar`/`bar_=` pair.

## Nullary parentheses seam
```scala
def size: Int = items.length   // accessor-like
def reload(): Unit = { ... }   // side effect

size
reload()
```

**Flow:** declare and call nullary methods consistently — `()` means side effects allowed; no `()` means accessor semantics.
**Invariant:** calling `reload` when defined as `reload()` (or vice versa) fails review; Scala 3 enforces at compile time.
**Probe:** scalafix/Scalafmt call-site rules; grep shows matching def/call paren style.

## Symbolic methods seam
```scala
// Acceptable: standard math/collection
def +(other: Money): Money
def ::(head: Int, tail: List[Int]): List[Int]

// Reject in application API
// channel ! msg
```

**Flow:** reserve symbolic names for math/standard library patterns or true DSLs — prefer `send(msg)` in application code.
**Invariant:** novel symbolic operators (`>>=`, `<<`) in domain API fail review.
**Probe:** grep non-standard operator defs in `src/` diff.

## Verdict
Java-style packages, camelCase discipline, accessor/mutator convention, parentheses signal effects. Learning note: `scala-style-learning-note.md`.
