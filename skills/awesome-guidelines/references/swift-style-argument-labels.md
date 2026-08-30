<!-- capsule-v2 -->
# Argument labels and parameters — do labels encode grammar?

**Source:** Swift API Design Guidelines §Parameters, §Argument Labels. **Question:** Do labels disambiguate arguments and replace method families?

## Labels seam
**Path/Symbol:** functions, methods, initializers.
**Signature:** first-argument label rules; prepositional phrases; defaults at end.
**Data Shape:** value-preserving conversions omit first label.

### Decisive pattern
```swift
func move(from start: Point, to end: Point)

employees.remove(at: position)

extension UInt32 {
    init(_ value: Int16)
    init(truncating source: UInt64)
}

view.dismiss(animated: false)
words.split(maxSplits: 12)
```

**Flow:** label prepositions (`at:`, `from:`) → omit label when args indistinguishable (`min(x,y)`) → conversion initializers use `_` first param when value-preserving → otherwise label all arguments after the first.
**Invariant:** `remove(x)` when `x` is an index (not element) fails review — needs `remove(at:)`.
**Probe:** call-site readability test; first arg without label must not start spurious phrase.

## Default parameters seam
```swift
extension String {
    func compare(
        _ other: String,
        options: CompareOptions = [],
        range: Range<Index>? = nil,
        locale: Locale? = nil
    ) -> ComparisonResult { /* ... */ }
}
```

**Flow:** replace method families with one method + defaults → put defaulted parameters last → hide irrelevant args at common call sites.
**Invariant:** overload set differing only by optional parameters at end should collapse to defaults.
**Probe:** count overload siblings with parallel docs — prefer single defaulted signature.

## Weak-type compensation seam
```swift
func addObserver(_ observer: NSObject, forKeyPath path: String)

grid.addObserver(self, forKeyPath: graphicsPath)
```

**Flow:** when parameter type is weak (`Any`, `NSObject`, `Int`), prepend role noun in signature (`forKeyPath`, `havingLength:`).
**Invariant:** `add(_:for:)` with vague second label on `String` param fails review.
**Probe:** call site reads clearly without reading parameter types.

## Overload ambiguity seam
```swift
mutating func append(_ newElement: Element)
mutating func append(contentsOf newElements: some Sequence<Element>)
```

**Flow:** when polymorphism causes ambiguity (e.g. `[Any]`), rename overloads explicitly (`append(contentsOf:)`).
**Invariant:** overload on return type alone is forbidden.
**Probe:** compiler ambiguity errors absent; `[Any]` append test documents chosen behavior.

## Verdict
Grammar-aware labels, defaults over families, explicit disambiguation. Learning note: `swift-style-learning-note.md`.
