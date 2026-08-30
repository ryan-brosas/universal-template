<!-- capsule-v2 -->
# Formatting and layout — does code match Kotlin official mechanical rules?

**Source:** Kotlin coding conventions §Formatting; Android style guide §Formatting. **Question:** Will ktlint/IntelliJ Kotlin style pass on changed files?

## Layout seam
**Path/Symbol:** `*.kt` source files.
**Signature:** 4-space indent; K&R braces; no semicolons; UTF-8.
**Data Shape:** trailing commas at declaration sites encouraged.

### Decisive pattern
```kotlin
class InvoiceService(
    private val repository: InvoiceRepository,
) {
    fun find(id: InvoiceId): Invoice? {
        return repository.find(id)
    }
}

fun process(items: List<Item>) {
    for (item in items) {
        handle(item)
    }
}
```

**Flow:** apply IntelliJ **Kotlin style guide** preset → 4-space indent → opening `{` on same line as header → closing `}` aligned with header start.
**Invariant:** tabs never used; line breaks significant — do not use Allman brace style.
**Probe:** ktlint/IDE formatter check exit 0; no tab characters in diff.

## Whitespace and modifiers seam
```kotlin
class A(val x: Int)

fun foo(x: Int): String = x.toString()

@VisibleForTesting
internal fun parse(input: String): Result =
    parser.parse(input)
```

**Flow:** space around binary operators → no space before call `(` → annotations before modifiers in prescribed order → omit redundant `public`.
**Invariant:** `foo (1)` and horizontal column alignment of `=` across unrelated lines fail review.
**Probe:** standard ktlint spacing/modifier-order rules clean.

## Trailing comma seam
```kotlin
data class Person(
    val firstName: String,
    val lastName: String,
    val age: Int,
)

enum class Status {
    ACTIVE,
    INACTIVE,
}
```

**Flow:** add trailing comma on multiline parameter/argument/enum lists at declaration site.
**Invariant:** single-line lists may omit comma; multiline declarations should include trailing comma for diff hygiene.
**Probe:** `trailing-comma-on-declaration-site` rule (ktlint) or IDE option enabled.

## Verdict
Adopt official 4-space Kotlin layout with modifier order and declaration trailing commas. Learning note: `kotlin-style-learning-note.md`.
