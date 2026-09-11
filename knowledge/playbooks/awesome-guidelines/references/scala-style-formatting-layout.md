<!-- capsule-v2 -->
# Formatting and layout — does code match Scala official mechanical rules?

**Source:** Scala style guide §Indentation, §Control Structures; Databricks §Spacing. **Question:** Will Scalafmt/project formatter pass on changed files?

## Indent seam
**Path/Symbol:** `*.scala` source files.
**Signature:** 2-space indent; no tabs; space after control keywords.
**Data Shape:** wrap continuation lines +2 spaces from expression start.

### Decisive pattern
```scala
class InvoiceService(repository: InvoiceRepository) {

  def find(id: InvoiceId): Option[Invoice] =
    repository.find(id)

  def process(items: List[Invoice]): List[Invoice] = {
    items.filter(_.total > 0)
  }
}
```

**Flow:** 2-space nested blocks → space after `if`/`for`/`while`/`match` keyword before `(`.
**Invariant:** 4-space or tab indent fails review; `if(foo)` without space fails review.
**Probe:** Scalafmt check exit 0; `cat -A` shows spaces not tabs.

## Line wrap seam
```scala
val result = 1 + 2 + 3 + 4 + 5 + 6 +
  7 + 8 + 9 + 10

foo(
  someVeryLongFieldName,
  andAnotherVeryLongFieldName,
  "literal",
  3.1415)
```

**Flow:** prefer intermediate vals over long wraps → when wrapping, indent +2 from first line → multiline calls: one arg per line indented +2.
**Invariant:** deep column alignment of args under opening `(` when method name changes fails review.
**Probe:** lines ≤ project max (80–100); formatter wrap rules clean.

## Control-structure seam
```scala
val news =
  if (condition)
    goodNews()
  else
    badNews()

for {
  x <- rows
  y <- cols
} yield (x, y)
```

**Flow:** functional single-expr `if`/`for-yield` may omit braces → multi-generator `for` with `yield` uses braces → loops without `yield` may use `(x <- xs; y <- ys)`.
**Invariant:** imperative multi-statement `if` without braces fails review.
**Probe:** review distinguishes functional vs imperative branches.

## Verdict
Adopt 2-space layout, keyword spacing, disciplined wraps. Learning note: `scala-style-learning-note.md`.
