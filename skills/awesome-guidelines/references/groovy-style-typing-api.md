<!-- capsule-v2 -->
# Typing and API — is the public contract explicit and checkable?

**Source:** Groovy style guide §21, §18, §20; CodeNarc conventions. **Question:** Will library consumers and static analysis understand boundaries?

## Typing seam
**Path/Symbol:** public classes, shared library methods, Gradle plugins.
**Signature:** explicit types on public API; assert preconditions.
**Data Shape:** CodeNarc type rules / `@CompileStatic` when project requires.

### Decisive pattern
```groovy
class OrderService {
    List<Order> findOpen(Customer customer) {
        assert customer
        orders.findAll { it.customerId == customer.id && it.open }
    }

    void close(Order order) {
        assert order?.id
        order.open = false
    }
}
```

**Flow:** public methods — always type parameters and returns; reserve `def` for private/local when IDE infers → never use `def` return type on methods where last statement might be assignment (accidental non-void return) → use Groovy `assert` for parameter/ invariant checks (always evaluated) → catch specific exceptions; use bare `catch (any)` only deliberately → strict libraries enable CodeNarc rules (`MethodParameterTypeRequired`, `VariableTypeRequired`, `@CompileStatic` when performance/safety policy demands).
**Invariant:** `def` on public API, missing asserts on critical preconditions, or untyped plugin entrypoints fails library review.
**Probe:** CodeNarc/npm-groovy-lint on `src/`; public method signature audit.

## Interop seam
**Flow:** when exposing to Java consumers, generated getters/setters from POGOs remain; document nullable boundaries; prefer typed collections in public signatures when Java calls in.
**Invariant:** Groovy-only `def` signatures on Java-facing modules fails review.
**Probe:** javac consumer compile against published API jar (if applicable).

## Verdict
Strong public types, assert guards, CodeNarc/static policy on libraries. Learning note: `groovy-style-learning-note.md`.
