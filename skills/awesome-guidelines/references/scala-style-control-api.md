<!-- capsule-v2 -->
# Control flow and API docs — are effects and documentation intentional?

**Source:** Scala style guide §Control, §Scaladoc; Databricks §Return, §Documentation; Scala Best Practices. **Question:** Is control flow functional by default and is public surface documented?

## Return and closure seam
**Path/Symbol:** methods with async callbacks, futures, collection ops.
**Signature:** expression-oriented methods; avoid `return` in inner closures.
**Data Shape:** `@tailrec` when recursion is required.

### Decisive pattern
```scala
def parseAll(input: String): Option[List[Invoice]] =
  for {
    line <- input.linesIterator.toList
    invoice <- parseLine(line)
  } yield invoice

def guardExample(value: Any): Option[String] =
  if (value == null) None
  else Some(value.toString)
```

**Flow:** prefer final expression over `return` → never `return` inside `{ ... }` passed to callbacks (`onComplete`, etc.) → use `for` comprehension over long `map`/`flatMap` chains when clearer → `@tailrec` only when recursion justified.
**Invariant:** `return` inside anonymous function argument fails review.
**Probe:** grep `return` inside nested blocks; compiler tailrec annotation where claimed.

## For-comprehension seam
```scala
val pairs =
  for {
    x <- board.rows
    y <- board.files
  } yield (x, y)

for (x <- board.rows; y <- board.files) {
  printf("(%d, %d)", x, y)
}
```

**Flow:** multi-generator with `yield` → brace form; effectful loop → paren/`;` form.
**Invariant:** wrong comprehension syntax for effect vs value fails review.
**Probe:** readability review on nested `flatMap` converted to `for`.

## Scaladoc seam
```scala
/** Finds an invoice by identifier.
  *
  * @param id the invoice id
  * @return the invoice if present
  */
def find(id: InvoiceId): Option[Invoice]
```

**Flow:** Scaladoc on every public package/class/trait/method → summary first line → `@param`/`@return` when helpful → link types with `[[Type]]`.
**Invariant:** new public member without Scaladoc summary fails review.
**Probe:** unidoc/scaladoc generation; API diff shows docs for new symbols.

## Error handling seam
```scala
def load(path: Path): Either[LoadError, Invoice] =
  parser.parse(Files.readString(path)).left.map(LoadError.apply)

def validate(input: UserInput): Validated[NonEmptyList[FieldError], Form] =
  validator.validate(input)
```

**Flow:** validation/user input errors as `Either`/`Validated`/typed ADT — not thrown exceptions → exceptions for truly exceptional/system faults only.
**Invariant:** throwing for expected validation failure fails review.
**Probe:** tests assert error channel without try/catch for happy path.

## Verdict
Expression-oriented control, documented public API, typed errors over throws. Learning note: `scala-style-learning-note.md`.
