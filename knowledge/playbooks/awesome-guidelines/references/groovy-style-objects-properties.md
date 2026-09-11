<!-- capsule-v2 -->
# Objects and properties — are beans POGO-idiomatic?

**Source:** Groovy style guide §7–10, §9 with/tap. **Question:** Is property access and mutation concise without Java boilerplate?

## POGO seam
**Path/Symbol:** domain classes and service beans.
**Signature:** property fields; `==` equality; named ctor maps.
**Data Shape:** `with` / `tap` mutation blocks.

### Decisive pattern
```groovy
class Server {
    String name
    Cluster cluster
}

def server = new Server(name: 'Obelix', cluster: aCluster)

server.with {
    status = 'running'
    sessionCount = 3
    start()
}

assert server.name == 'Obelix'
assert !server.is(otherServer)
```

**Flow:** POGO implicit properties instead of hand-written getters/setters → property notation (`obj.prop`) for Groovy consumers → construct with named parameters on default ctor → batch mutations with `with { }` (last expr returned) or `tap { }` (returns receiver) → use Groovy `==` for null-safe value equality; `is()` for reference identity.
**Invariant:** Java-style getter chains in Groovy-only code, manual POJO boilerplate, or `==` for reference identity fails review.
**Probe:** grep `\.get[A-Z]` in internal Groovy; equality usage audit.

## Visibility seam
**Flow:** omit `public`; use `@PackageScope` for package visibility when needed.
**Invariant:** noisy `public` on every member fails review.
**Probe:** style grep `public class` in Groovy tree.

## Verdict
POGO properties, named construction, with/tap, == vs is. Learning note: `groovy-style-learning-note.md`.
