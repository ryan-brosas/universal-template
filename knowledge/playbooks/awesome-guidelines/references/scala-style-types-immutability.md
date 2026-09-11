<!-- capsule-v2 -->
# Types and immutability — are public APIs explicit and data immutable?

**Source:** Scala style guide §Types; Databricks §Type Inference, §Case Classes; Scala Best Practices §2. **Question:** Are public methods typed, case classes immutable, and Option used safely?

## Type inference seam
**Path/Symbol:** methods and vals across application code.
**Signature:** infer private/obvious locals; explicit public return types.
**Data Shape:** function types written `Int => String` without extra parens on arity-1.

### Decisive pattern
```scala
final case class Invoice(id: InvoiceId, total: BigDecimal)

trait InvoiceService {
  def find(id: InvoiceId): Option[Invoice]
  def listOpen(): List[Invoice]
}

private val defaultLimit = 100

def parseIds(raw: String): List[InvoiceId] =
  raw.split(",").toList.map(InvoiceId.apply)
```

**Flow:** public defs always annotate return type → private vals infer when RHS obvious → function params infer when type known from expected type (e.g. `map(x => ...)`).
**Invariant:** public `def find(id) =` without return type fails review.
**Probe:** wartremover/Scalafix explicit public type rules; API readers need not infer from body.

## Immutability seam
```scala
final case class Person(name: String, age: Int)

def bumpAge(person: Person): Person =
  person.copy(age = person.age + 1)
```

**Flow:** prefer `val` and immutable collections → case classes with immutable params → `copy` for updates → case classes `final`.
**Invariant:** `var` in case class or mutable constructor param fails review.
**Probe:** grep `var` in case class definitions; tests use immutable transforms.

## Override and Option seam
```scala
trait Repository {
  def find(id: InvoiceId): Option[Invoice]
}

final class JdbcRepository extends Repository {
  override def find(id: InvoiceId): Option[Invoice] = {
    fetch(id).filter(_.isActive)
  }
}

def title(invoice: Invoice): String =
  invoice.title.getOrElse("Untitled")
```

**Flow:** always `override` when implementing/overriding → Option instead of null → never `.get` without proof → don't catch `Throwable`.
**Invariant:** missing `override`, `Option.get`, and `null` literals fail review.
**Probe:** `-Xfatal-warnings` / lint rules for override; grep `.get` on Option in diff.

## Constants seam
```scala
object Configuration {
  val DefaultPort = 10000   // official UpperCamelCase style
}

object Limits {
  val MAX_RETRIES = 3       // Spark/Java-interop style — pick one per repo
}
```

**Flow:** choose one constant convention per codebase (UpperCamelCase per scala-lang **or** SCREAMING_SNAKE per Databricks/Spark) and apply consistently in companions.
**Invariant:** mixed `DefaultPort` and `MAX_RETRIES` styles in same module fail review.
**Probe:** naming lint scoped to `object` companions.

## Verdict
Explicit public types, immutable case classes, override always, Option discipline. Learning note: `scala-style-learning-note.md`.
