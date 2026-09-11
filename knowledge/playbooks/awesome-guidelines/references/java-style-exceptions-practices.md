<!-- capsule-v2 -->
# Exceptions and practices — are overrides explicit and catches handled?

**Source:** Google javaguide §6; Alibaba §2 Exception. **Question:** Will silent catches and missing `@Override` hide bugs?

## Override & static seam
```java
@Override
public String toString() {
  return "Order{id=" + id + "}";
}

@Override
public boolean equals(Object obj) {
  if (!(obj instanceof Order other)) {
    return false;
  }
  return Objects.equals(this.id, other.id);
}

public void reset() {
  OrderState.clearCache(); // good — class-qualified static
}
```

**Flow:** annotate every legal override → qualify static members with declaring class → never override `finalize`.
**Invariant:** removing `@Override` must not compile if super signature drifts — catches API drift at build time.
**Probe:** compiler/Checkstyle `@Override` on overrides; static access via class name in review.

## Catch seam
```java
try {
  return Integer.parseInt(response);
} catch (NumberFormatException ignored) {
  // Not numeric; fall through to text handling — justified in comment
}
return handleTextResponse(response);
```

**Flow:** on catch → log, rethrow, translate, or document why empty → never silent empty catch → prefer pre-check over catching NPE/IOOBE when cheap (Alibaba).
**Invariant:** empty catch requires comment explaining safety; runtime JDK exceptions not used for control flow when pre-check exists.
**Probe:** grep `catch[^{]*\{\s*\}` without nearby comment fails review.

## Verdict
Adopt `@Override`, qualified statics, documented catch handling. Learning note: `java-style-learning-note.md`.
