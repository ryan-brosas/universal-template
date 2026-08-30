<!-- capsule-v2 -->
# Naming and types — are identifiers predictable without Hungarian noise?

**Source:** Google javaguide §5; Alibaba naming §1. **Question:** Do class/member names match ecosystem tooling and acronym rules?

## Naming seam
**Path/Symbol:** packages, classes, fields, methods, constants.
**Signature:** no `mName`/`s_` prefixes; camelCase algorithm for acronyms.
**Data Shape:** `UpperCamelCase` types, `lowerCamelCase` members, true constants only as `UPPER_SNAKE_CASE`.

### Decisive table
```java
package com.example.deepspace;

public class XmlHttpRequest { }

public class OrderService {
  private static final int MAX_PAGE_SIZE = 100;
  private final OrderRepository orderRepository;

  public CustomerId findCustomerId(String rawId) { ... }
}

class HashIntegrationTest { }
```

**Flow:** prose name → Google camelCase algorithm → apply kind-specific case → test classes end with `Test`.
**Invariant:** only deeply immutable `static final` fields are constants — locals never `UPPER_SNAKE_CASE` even if `final`.
**Probe:** review rejects Hungarian prefixes; acronym names match table (`newCustomerId` not `newCustomerID`).

## Type habits (Alibaba secondary)
**Flow:** POJO/RPC fields use wrapper types when null is meaningful → no magic literals — named constants → `equals` invoked on known-non-null constant.
**Invariant:** `"ACTIVE".equals(status)` not `status.equals("ACTIVE")` when status may be null.
**Probe:** nullable domain fields use `Integer`/`Boolean` wrappers where NPE distinction matters (project convention doc).

## Verdict
Adopt Google naming matrix + acronym rules; Alibaba null-safe equals for nullable strings. Learning note: `java-style-learning-note.md`.
