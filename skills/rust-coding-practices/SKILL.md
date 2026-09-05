---
name: rust-coding-practices
description: "Use when authoring or reviewing Rust, rustfmt defaults, RFC 430 naming, meaningful Error types, Result/? in docs, common trait impls, iter/into_iter conventions, and predictable public APIs."
invocation: manual
disable-model-invocation: true
---

# Rust Coding Practices

Application skill for Rust style learning (from the archived `awesome-guidelines` style capsules). For async/concurrency or framework crates, combine with stack-specific guidance.

## Core Principle

Follow the project rustfmt, lint, and API conventions. The retained API-guideline
capsules are options for predictable public surfaces, not universal requirements
for every type or private helper.

## When to Use / NOT

- Rust library/application code, public API design, CI setup.
- Reviewing `Result` types, error enums, or rustdoc.

**NOT when:**

- Non-Rust code.
- Macro-heavy generated code, validate generator output, not hand-edits.

## Workflow

1. **Format & names**, `cargo fmt`, casing, conversion prefixes (`rust-style-formatting-naming.md`).
2. **Errors**, choose useful error information for callers. Add `Error`, `Send`,
   or `Sync` bounds where consumers/runtime boundaries require them; a local
   sentinel error can be enough (`rust-style-errors-result.md`).
3. **Interop**, common traits, `From`, iterator naming (`rust-style-traits-interop.md`).
4. **API shape**, methods, `new`, no out-params, Deref discipline, docs (`rust-style-api-predictability.md`).
5. **Verify**, `cargo fmt --check`, `cargo clippy`, `cargo test --doc`.

## Red Flags

- `Result<T, ()>` losing distinctions a caller needs
- `unwrap()` in public docs
- `get_*` on ordinary field getters
- `Deref` on domain wrapper for `.` syntax sugar
- Manual formatting vs rustfmt
- Missing useful diagnostics on public types, or diagnostics exposing secrets

## Verification

- `cargo fmt --check`, `cargo clippy -- -D warnings` (project policy)
- Doctests pass with `?` pattern
- Capsule checklist on public API review


## References

- `awesome-guidelines/references/rust-style-learning-note.md`
- `awesome-guidelines/references/rust-style-formatting-naming.md`
- `awesome-guidelines/references/rust-style-errors-result.md`
- `awesome-guidelines/references/rust-style-traits-interop.md`
- `awesome-guidelines/references/rust-style-api-predictability.md`
