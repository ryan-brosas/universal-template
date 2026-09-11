<!-- capsule-v2 -->
# Documentation and types — is every declaration documented and well-placed?

**Source:** Swift API Design Guidelines §Fundamentals, §Conventions. **Question:** Does public API have summaries and appropriate method/property factoring?

## Documentation seam
**Path/Symbol:** all declarations; public API required.
**Signature:** Swift-flavored Markdown `///` summary per entity.
**Data Shape:** non-O(1) computed properties note complexity.

### Decisive pattern
```swift
/// Returns a view of `self` with elements in reverse order.
func reversed() -> ReverseCollection<Self> { /* ... */ }

/// Inserts `newHead` at the beginning of `self`.
mutating func prepend(_ newHead: Element) { /* ... */ }

/// A collection supporting equally efficient insertion/removal at any position.
struct List<Element> {
    /// The element at the beginning of `self`, or `nil` if empty.
    var first: Element? { /* ... */ }

    /// - Complexity: O(*n*), where *n* is the length of `self`.
    var normalizedEntries: [Entry] { /* ... */ }
}
```

**Flow:** write summary first (design aid) → describe function as verb + return → subscripts as access → types as nouns → add `- Parameter`/`- Returns` when needed.
**Invariant:** new public declaration without `///` summary fails review.
**Probe:** doc lint / review checklist; Xcode Quick Help renders meaningful summary.

## Methods vs free functions seam
```swift
// Preferred — instance method
extension String {
    func padded(to length: Int) -> String { /* ... */ }
}

// Acceptable free functions
min(x, y, z)
print(value)
sin(x)
```

**Flow:** prefer methods/properties on type → free functions only when no logical `self`, unconstrained generic utility, or domain notation (`sin`).
**Invariant:** free function that clearly belongs on type (`parseJSON(_:)`) fails review.
**Probe:** API surface groups behavior with owning type.

## Tuple and closure clarity seam
```swift
mutating func ensureUniqueStorage(
    minimumCapacity requestedCapacity: Int,
    allocate: (_ byteCount: Int) -> UnsafeRawPointer
) -> (reallocated: Bool, capacityChanged: Bool)
```

**Flow:** label tuple members and closure parameters in signature for documentation cross-reference.
**Invariant:** opaque `(Bool, Bool)` return without named tuple members on public API fails review.
**Probe:** generated docs show tuple field names; closure param names match top-level param style.

## Verdict
Document every declaration; prefer methods; label tuple/closure API clearly. Learning note: `swift-style-learning-note.md`.
