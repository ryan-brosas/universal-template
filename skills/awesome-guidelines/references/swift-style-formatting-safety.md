<!-- capsule-v2 -->
# Formatting and safety — is Swift code safe and access-explicit?

**Source:** GitHub Swift style guide; Swift API guidelines (fundamentals). **Question:** Does code default to immutability and avoid force-unwrap footguns?

## Immutability and control flow seam
**Path/Symbol:** application `*.swift` sources.
**Signature:** `let` by default; `guard` for preconditions; optional binding over force-unwrap.
**Data Shape:** explicit access control on top-level definitions.

### Decisive pattern
```swift
public struct InvoiceService {
    private let repository: InvoiceRepository

    public init(repository: InvoiceRepository) {
        self.repository = repository
    }

    public func find(id: InvoiceID) -> Invoice? {
        guard let invoice = repository.find(id: id) else {
            return nil
        }
        return invoice
    }
}
```

**Flow:** bind with `let` → validate with `guard … else { return/throw }` → use `if let` / optional chaining instead of `!`.
**Invariant:** force-unwrap (`value!`) and implicitly unwrapped optionals (`Type!`) in application code fail review without documented invariant.
**Probe:** SwiftLint `force_unwrapping` / `implicitly_unwrapped_optional` rules; grep `\!` on optional bindings in diff.

## Access and type choice seam
```swift
public enum InvoiceError: Error {
    case notFound
}

internal struct Parser {
    func parse(_ text: String) throws -> Invoice { /* ... */ }
}

public final class LegacyBridge {
    private var handle: Handle

    init(handle: Handle) {
        self.handle = handle
    }
}
```

**Flow:** top-level types/functions/vars declare `public`/`internal`/`private` explicitly → prefer `struct`/`enum` → classes `final` unless designed for subclassing.
**Invariant:** open non-final class without documented extension point fails review.
**Probe:** explicit access on new top-level symbols; `final` on new classes unless `open`/`class` intent documented.

## Style mechanics seam
```swift
let timeout: TimeInterval = 2
let capitals: [Country: City] = [:]

var count: Int {
    storage.count
}

func makeCoffee(type: CoffeeType) -> Coffee { /* ... */ }
```

**Flow:** colon sticks to identifier (`name: Type`) → omit explicit `get` on read-only computed properties → omit `self` except where required.
**Invariant:** `get { }` wrapper on trivial read-only computed property fails review.
**Probe:** review checklist; project SwiftFormat profile applied in CI.

## Verdict
Prefer let, guard, safe optionals, explicit access, struct/final defaults. Learning note: `swift-style-learning-note.md`.
