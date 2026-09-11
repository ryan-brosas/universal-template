<!-- capsule-v2 -->
# Naming and API fluency — do use sites read as clear English?

**Source:** Swift API Design Guidelines §Naming. **Question:** Are names role-based, fluent at call site, and free of redundant type words?

## Role-based naming seam
**Path/Symbol:** public/internal API surface.
**Signature:** names describe roles, not type constraints; omit needless type words.
**Data Shape:** boolean names read as assertions about receiver.

### Decisive pattern
```swift
protocol ViewController {
    associatedtype ContentView: View
}

class ProductionLine {
    func restock(from supplier: WidgetFactory) { /* ... */ }
}

extension Shape {
    func contains(_ other: Point) -> Bool { /* ... */ }
    var isEmpty: Bool { /* ... */ }
}
```

**Flow:** rename `widgetFactory` → role noun (`supplier`) → drop redundant `Element` suffixes (`remove(_:)` not `removeElement(_:)`) → booleans as assertions (`isEmpty`, `intersects`).
**Invariant:** parameter named after its type (`string: String`) when role is obvious fails review.
**Probe:** read call sites aloud — ambiguous phrases (`remove(x)` vs `remove(at: x)`) fail review.

## Fluent usage seam
```swift
list.insert(item, at: index)
view.addSubview(child)
names = words.capitalizingNouns()
let iterator = collection.makeIterator()
```

**Flow:** method names form grammatical phrases at use site → factory methods use `make` prefix → side-effect-free methods read as noun phrases, mutating as imperatives.
**Invariant:** awkward pseudo-English (`nounCapitalize()`, `subviews(color:)`) fails review.
**Probe:** API review reads invocation as sentence; mutating method uses verb imperative.

## Mutating pairs seam
```swift
mutating func sort() { /* in place */ }
func sorted() -> [Element] { /* copy */ }

mutating func stripNewlines() { /* ... */ }
func strippingNewlines() -> String { /* ... */ }
```

**Flow:** mutating verb ↔ nonmutating `-ed`/`-ing` counterpart (`sort`/`sorted`, `stripNewlines`/`strippingNewlines`).
**Invariant:** mutating/nonmutating pair with inconsistent naming fails review.
**Probe:** stdlib-style pairing check on collection-like APIs.

## Case and protocols seam
```swift
var utf8Bytes: [UTF8.CodeUnit]
var isRepresentableAsASCII = true

protocol Collection { /* ... */ }
protocol ProgressReporting { /* ... */ }
```

**Flow:** UpperCamelCase types/protocols; lowerCamelCase members; acronyms sized consistently (`utf8`, `URLSession` rules per guideline).
**Invariant:** `URLSession` vs `UrlSession` inconsistency fails review.
**Probe:** swift-api-digester / naming lint if configured; manual acronym scan.

## Verdict
Name for clarity at point of use — roles, fluency, consistent mutating pairs. Learning note: `swift-style-learning-note.md`.
