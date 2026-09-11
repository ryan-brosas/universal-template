<!-- capsule-v2 -->
# Collections and GDK — are data and control flow Groovy-expressive?

**Source:** Groovy style guide §12–14, §16–19. **Question:** Are collections manipulated with GDK and null-safe operators?

## GDK seam
**Path/Symbol:** list/map processing and branching.
**Signature:** GDK higher-order methods; Groovy truth; safe navigation.
**Data Shape:** native literals and powerful switch.

### Decisive pattern
```groovy
def activeNames = users
    .findAll { it.enabled }
    .collect { it.name }

def status = order?.customer?.address?.city ?: 'Unknown'

switch (value) {
    case 0..10: 'small'
    case Number: 'number'
    case { it > 100 }: 'large'
    default: 'other'
}
```

**Flow:** prefer `each`/`findAll`/`collect`/`inject` over manual index loops → use `in` for membership → leverage multiline GStrings or `\` continuations for long messages → Groovy truth (`if (name)`) instead of explicit null/empty checks → safe navigation `?.` chains → Elvis `?:` for defaults → expressive `switch` on ranges, types, lists, closures when it clarifies branching.
**Invariant:** nested null `if` ladders, Java-style `+` string build, or manual for-index loops where GDK fits fails review.
**Probe:** grep `!= null &&`; GDK method usage ratio on collections.

## Data literal seam
```groovy
def ports = [8080, 8443]
def headers = [Accept: 'application/json']
assert 8080 in ports
```

**Flow:** native list/map/range/regex literals; `<<` append where idiomatic.
**Invariant:** verbose `new ArrayList()`/`new HashMap()` in Groovy scripts fails review.
**Probe:** collection construction style spot check.

## Verdict
GDK iterators, Groovy truth, ?. and ?:, native literals. Learning note: `groovy-style-learning-note.md`.
