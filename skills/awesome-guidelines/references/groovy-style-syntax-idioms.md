<!-- capsule-v2 -->
# Syntax and idioms — is the surface Groovy-native not Java-pasted?

**Source:** groovy-lang.org style guide §1–6, §11–12, §15. **Question:** Does code read idiomatic without Java ceremony?

## Syntax seam
**Path/Symbol:** `.groovy` sources and Gradle scripts.
**Signature:** no semicolons; no redundant `def`; minimal parentheses.
**Data Shape:** GStrings and native collection literals.

### Decisive pattern
```groovy
class Server {
    String name

    String describe(Cluster cluster) {
        "server $name in ${cluster.id}"
    }
}

def ids = items.findAll { it.active }.collect { it.id }
def config = [CA: 'California', WA: 'Washington']
```

**Flow:** omit semicolons → drop redundant `public` and `return` on short methods → never combine `def` with a type (`String name`, not `def String name`) → omit empty `()` before trailing closures (`list.each { … }`) → use GStrings for interpolation; single quotes for constants → native `[ ]`, `[ : ]`, `1..10`, `~/pattern/` → import aliasing for name clashes (`import java.util.List as UtilList`).
**Invariant:** semicolon-terminated lines, `def String`, or `each() { }` empty-paren form fails idiomatic review.
**Probe:** CodeNarc `UnnecessarySemicolon`; visual style pass.

## Class literal seam
```groovy
connection.doPost("${baseUri}/modify", params, ResourcesResponse)
```

**Flow:** omit `.class` suffix when passing class literals in Groovy APIs.
**Invariant:** Java-style `.class` where Groovy literal suffices fails review in pure Groovy modules.
**Probe:** grep `\.class\)` in Groovy sources.

## Verdict
Semicolon-free, typed-not-def, parenless closures, GStrings and native literals. Learning note: `groovy-style-learning-note.md`.
