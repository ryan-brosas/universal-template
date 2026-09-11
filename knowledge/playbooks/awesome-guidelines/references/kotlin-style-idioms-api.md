<!-- capsule-v2 -->
# Idioms and library API — is Kotlin used idiomatically?

**Source:** Kotlin coding conventions §Idiomatic use, §Coding conventions for libraries. **Question:** Does code prefer immutability, expression forms, and stable public API?

## Immutability seam
**Path/Symbol:** application and library Kotlin sources.
**Signature:** `val` default; immutable collection interfaces in API surface.
**Data Shape:** default parameter values instead of overload sets.

### Decisive pattern
```kotlin
fun validate(value: String, allowed: Set<String>) { /* ... */ }

fun load(path: Path, encoding: Charset = Charsets.UTF_8): String { /* ... */ }

fun buildResponse(status: Int, cached: Boolean = false): Response =
    Response(status = status, cached = cached)
```

**Flow:** declare locals/properties as `val` unless mutated → expose `Set`/`List`/`Map` not mutable concrete types → `listOf()`/`setOf()` for immutable literals → default args replace overload triples.
**Invariant:** `var` without reassignment, `HashSet` parameter types, and `fun foo()` + `fun foo(a: String)` overload pair fail review.
**Probe:** inspection highlights unnecessary `var`; public API grep shows interface types not `ArrayList`/`HashMap`.

## Control-flow seam
```kotlin
fun label(count: Int?): String =
    when {
        count == null -> "unknown"
        count == 0 -> "empty"
        else -> "nonzero"
    }

fun firstOrNull(items: List<String>): String? =
    if (items.isEmpty()) null else items.first()
```

**Flow:** prefer expression `if`/`when`/`try` for single-result branches → binary null check uses `if`, not `when` → named args when multiple same-type primitives/`Boolean`.
**Invariant:** statement-form early returns when expression form is clearer fail review; `when` with only null/else for binary case fails review.
**Probe:** review flags multi-arg calls with ambiguous positional primitives lacking names.

## Library API seam
```kotlin
/**
 * Parses invoices from [input].
 */
public fun parseInvoices(input: String): List<Invoice> { /* ... */ }

internal class DefaultParser : Parser {
    internal fun configure(options: Options): Unit { /* ... */ }
}
```

**Flow:** libraries specify visibility explicitly → public functions/properties declare return types → KDoc on public members (except trivial overrides).
**Invariant:** public API with omitted return type or missing docs on new exported member fails review.
**Probe:** API snapshot / dokka module; explicit `: Type` on public declarations in diff.

## Scope functions (probe only)
**Flow:** choose `let`/`run`/`with`/`apply`/`also` per Kotlin scope-functions doc — avoid nested labeled returns in lambdas.
**Invariant:** deeply nested scope chains obscuring side effects fail review.
**Probe:** human review + detekt complexity rules if configured.

## Verdict
Prefer val, immutable types, default parameters, expression control flow, explicit library API. Learning note: `kotlin-style-learning-note.md`.
