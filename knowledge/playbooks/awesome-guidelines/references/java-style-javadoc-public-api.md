<!-- capsule-v2 -->
# Javadoc and public API — is visible surface documented for readers?

**Source:** Google javaguide §7. **Question:** Do public/protected members have usable Javadoc summaries?

## Javadoc seam
**Path/Symbol:** public/protected classes, methods, fields, record components.
**Signature:** `/** ... */` block; summary fragment first; tags `@param` `@return` `@throws`.
**Data Shape:** summary reads as capitalized sentence fragment; not bare `@return` tag alone.

### Decisive contrast
```java
/**
 * Returns the customer identifier associated with this order.
 *
 * @param rawId external id from the request payload
 * @return normalized customer id
 * @throws InvalidIdException if {@code rawId} is blank or malformed
 */
public CustomerId parseCustomerId(String rawId) throws InvalidIdException {
  ...
}
```

**Flow:** document every visible member unless truly self-explanatory and complete → write summary sentence → ordered block tags with non-empty descriptions.
**Invariant:** summary appears in indexes — must stand alone; overrides may omit Javadoc when identical to super.
**Probe:** javadoc task/warnings on public API; spot-check no `/** @return the foo */` one-liners.

## API clarity seam
**Flow:** overloads stay contiguous → class contents follow logical order explainable to maintainer → implementation comments become Javadoc when they define contract.
**Invariant:** new public methods ship with Javadoc in same change unless trivial getter with obvious name.
**Probe:** PR review checklist for public API delta includes Javadoc.

## Verdict
Adopt summary-first Javadoc on visible API; ordered tags; logical member grouping. Learning note: `java-style-learning-note.md`.
