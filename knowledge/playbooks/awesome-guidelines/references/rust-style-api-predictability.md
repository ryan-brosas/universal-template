<!-- capsule-v2 -->
# API predictability — does the surface behave how it looks?

**Source:** API guidelines Predictability + Documentation chapters (C-METHOD, C-NO-OUT, C-DEREF, C-CTOR, C-EXAMPLE). **Question:** Will rustdoc and method resolution surprise callers?

## Method & constructor seam
**Path/Symbol:** public inherent impls.
**Signature:** `Type::new()` primary constructor; methods for receiver-clear operations.
**Data Shape:** return `(T, U)` tuples instead of out-parameters.

### Decisive contrast
```rust
// Prefer
impl Service {
    pub fn new(config: Config) -> Self { ... }
    pub fn process(&self, item: Item) -> Result<Output, Error> { ... }
}

// Not
pub fn process(service: &Service, item: Item, out: &mut Output) -> Error { ... }
```

**Flow:** obvious receiver → method → multi-value returns via tuple/struct → static `new`/`with_*`/`from_*` for construction.
**Invariant:** no out-parameters except buffer-reuse APIs (`read(&mut buf)`); free functions only when no natural receiver.
**Probe:** public API review: methods vs `fn foo(x: &Foo)`; constructors are inherent static methods.

## Smart pointer & docs seam
**Flow:** only smart pointers implement `Deref`/`DerefMut` → hide impl details with `pub(crate)` / `#[doc(hidden)]` → every public item has runnable example where reasonable.
**Invariant:** `Deref` is not syntactic sugar for domain types; rustdoc shows user-relevant impls only.
**Probe:** no `impl Deref` on non-pointer wrapper types; crate-level docs + examples on primary types.

## Verdict
Adopt methods, tuple returns, smart-pointer-only Deref, thorough rustdoc. Learning note: `rust-style-learning-note.md`.
