<!-- capsule-v2 -->
# Formatting and imports — does layout match Google Java mechanical rules?

**Source:** Google javaguide §4, §3.3. **Question:** Will Checkstyle/google-java-format and import hygiene pass review?

## Format seam
**Path/Symbol:** `*.java` compilation units.
**Signature:** UTF-8; 2-space indent; 100-column wrap; K&R braces.
**Data Shape:** one top-level class per file; one statement per line.

### Decisive pattern
```java
if (condition) {
  doWork();
} else {
  cleanup();
}

public final class OrderService {
  private static final int MAX_RETRIES = 3;

  public Result process(Order order) {
    validate(order);
    return execute(order);
  }
}
```

**Flow:** apply google-java-format (or equivalent) → always brace control flow → wrap at 100 with continuation indent +4 from start.
**Invariant:** tabs never used; empty catch in multi-block `try/catch` cannot use `{}` on same line as catch.
**Probe:** formatter check in CI; grep shows no tab indent; no single-line `if (x) doThing();` without braces.

## Import seam
```java
import static com.example.Foo.DEFAULT;

import com.example.Bar;
import com.example.Baz;
import java.util.List;
```

**Flow:** static imports grouped → blank line → non-static ASCII sorted → no wildcards → no line-wrapped imports.
**Invariant:** wildcard `import pkg.*` is a review reject; one public class per file name.
**Probe:** Checkstyle `AvoidStarImport`; file name matches public class.

## Verdict
Adopt 2-space/100-col/braces and strict import groups. Learning note: `java-style-learning-note.md`.
