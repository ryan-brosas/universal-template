# Rust style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `rust-style-*.md` capsules, `rust-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Rust Style Guide](https://github.com/rust-lang/rust/tree/HEAD/src/doc/style-guide/src) | Default style = `rustfmt`; 4-space indent; 100-col lines; block indent; trailing commas; snake_case / UpperCamelCase / SCREAMING_SNAKE_CASE; expression-oriented code |
| [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) | Public API checklist: naming (RFC 430), `as_`/`to_`/`into_`, meaningful `Error + Send + Sync`, common traits, methods not free functions, no out-params, docs with `?` not `unwrap`, `# Errors`/`# Panics`/`# Safety` sections |
| Effective Go overlap (error flow analogy) | Rust uses `Result` + `?`; library code avoids panic; defer → Rust `Drop` + explicit `?` |

**Not duplicated here:** Full API guidelines checklist (100+ items) — capsules cover highest-leverage public-API seams. Async/concurrency deep dives — stack capsules in `skills/*-foundation` when needed.

## Mental model

Rust splits **mechanical style** from **API design**:

1. **Format** — `rustfmt` defaults (4 spaces, 100 cols, trailing commas, block indent). Don't fight the formatter.
2. **Naming** — types `UpperCamelCase`, values `snake_case`, constants `SCREAMING_SNAKE_CASE`; conversion prefixes encode cost/ownership.
3. **Public API** — every exported error is a real type implementing `Error + Send + Sync`; never `Result<T, ()>`.
4. **Predictability** — methods with receivers; `new` constructors; `iter`/`iter_mut`/`into_iter`; only smart pointers `Deref`.
5. **Docs** — examples propagate errors with `?`; document failure modes.

## Decision tables

### Formatting (style guide)

| Topic | Rule |
|---|---|
| Tool | `rustfmt` / `cargo fmt` |
| Indent | 4 spaces, block indent |
| Width | 100 chars max |
| Commas | trailing comma before newline in lists |
| Blank lines | 0–1 between items |
| Expressions | prefer `let x = if …` over mutate-then-assign |

### Naming (RFC 430 + API guidelines)

| Item | Convention |
|---|---|
| Types/traits/enums | `UpperCamelCase` (`Uuid` not `UUID`) |
| Functions/methods/locals | `snake_case` |
| Constants/statics | `SCREAMING_SNAKE_CASE` |
| Conversions | `as_` free borrow, `to_` expensive, `into_` consuming |
| Getters | `first()` not `get_first()` (exceptions: `Cell::get`) |
| Iterators | `iter`, `iter_mut`, `into_iter` → `Iter`, `IterMut`, `IntoIter` |

### Errors & API surface

| Case | Rule |
|---|---|
| Fallible public fn | `Result<T, E>` with meaningful `E` |
| Error type | `Error + Send + Sync + Display`; lowercase message, no trailing `.` |
| Never | `Result<T, ()>` |
| Docs/examples | `?` in doctests, not `unwrap()` |
| Panic | document `# Panics`; library avoids panic for recoverable cases |
| Traits on new types | implement common traits (`Debug`, `Clone`, `Eq`, …) where applicable |

### Predictability

| Case | Rule |
|---|---|
| Receiver obvious | method not free function |
| Multi-return | tuple/struct, not `&mut` out-param |
| `Deref` | smart pointers only |
| Conversions | on most specific type |
| Struct fields | private by default for future-proofing |

## Anti-patterns

- `fn foo() -> Result<Bar, ()>`
- `unwrap()` in public rustdoc examples
- `get_*` getters everywhere
- `Deref` on domain types for syntax sugar
- Fighting `rustfmt` with manual layout
- `-rs` crate name suffix
- Negative Cargo features (`no-std`)

## Skill trace

| Artifact | Role |
|---|---|
| `rust-style-formatting-naming.md` | rustfmt, casing, conversions |
| `rust-style-errors-result.md` | error types, Result, docs |
| `rust-style-traits-interop.md` | common traits, iterators, From |
| `rust-style-api-predictability.md` | methods, constructors, Deref, docs |
| `rust-coding-practices` | application skill |
