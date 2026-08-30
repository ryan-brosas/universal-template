<!-- capsule-v2 -->
# Errors and Result — are fallible APIs typed and documented?

**Source:** API guidelines C-GOOD-ERR, C-FAILURE, C-QUESTION-MARK. **Question:** Can callers use `?` and error crates without `()` or silent panic?

## Error type seam
**Path/Symbol:** public `Result<T, E>` APIs.
**Signature:** `E: Error + Send + Sync + 'static`; `Display` message lowercase, no trailing period.
**Data Shape:** unit struct or enum variants with context — never `()`.

### Decisive contrast
```rust
// Wrong
pub fn load(path: &Path) -> Result<Data, ()> { ... }

// Right
#[derive(Debug)]
pub struct LoadError { /* ... */ }

impl std::error::Error for LoadError {}
impl fmt::Display for LoadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "failed to load configuration")
    }
}

pub fn load(path: &Path) -> Result<Data, LoadError> { ... }
```

**Flow:** define crate-specific error → implement `Error + Display + Send + Sync` → return `Result` → document `# Errors` / `# Panics` on public items.
**Invariant:** never `Result<T, ()>`; library functions don't panic for expected failures.
**Probe:** public API grep for `Result<[^,]+, \(\)>` empty; errors implement `std::error::Error`.

## Docs & examples seam
````rust
/// ```rust
/// # fn main() -> Result<(), Box<dyn std::error::Error>> {
/// let data = mycrate::load("config.toml")?;
/// # Ok(())
/// # }
/// ```
````

**Flow:** doctests propagate with `?` → hide boilerplate with `#` lines → avoid `unwrap()` in copy-pasted examples.
**Invariant:** examples teach error-aware usage, not panic-on-failure habits.
**Probe:** rustdoc tests compile; public examples lack bare `.unwrap()` unless illustrating panic docs.

## Verdict
Adopt meaningful error types, `?` in docs, documented failure modes. Learning note: `rust-style-learning-note.md`.
