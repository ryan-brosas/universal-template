<!-- capsule-v2 -->
# Traits and iterators — do new types interoperate with the ecosystem?

**Source:** API guidelines C-COMMON-TRAITS, C-CONV-TRAITS, C-ITER, C-ITER-TY, C-COLLECT. **Question:** Can callers use `?`, iterators, and standard conversions without orphan impl frustration?

## Common traits seam
**Path/Symbol:** exported struct/enum types.
**Signature:** `Debug` on all public types; `Clone`/`Copy`/`Eq`/`Hash` when sensible.
**Data Shape:** `From`/`TryFrom`/`AsRef` instead of ad-hoc converters.

### Decisive pattern
```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserId(u64);

impl From<u64> for UserId {
    fn from(id: u64) -> Self { UserId(id) }
}

impl UserList {
    pub fn iter(&self) -> Iter<'_, User> { ... }
    pub fn iter_mut(&mut self) -> IterMut<'_, User> { ... }
    pub fn into_iter(self) -> IntoIter<User> { ... }
}
```

**Flow:** new public type → eagerly impl applicable std traits → collections expose `iter*` trio with matching type names → prefer `From` over bespoke `from_*` when unambiguous.
**Invariant:** avoid orphan pain for downstream — if `Display`/`Clone` applies, impl it on your type now.
**Probe:** missing `Debug` on public types flagged in review; iterator method names match return types.

## Serde & features seam
**Flow:** optional `serde` feature name exactly `"serde"`; additive features only.
**Invariant:** feature names have no placeholder fluff (`std` not `use-std`).
**Probe:** `Cargo.toml` features follow guidelines; no `no-*` negative features.

## Verdict
Adopt common traits, standard conversions, RFC 199 iterators. Learning note: `rust-style-learning-note.md`.
