---
name: rust-coding-practices
description: "Use when authoring or reviewing Rust, rustfmt defaults, RFC 430 naming, meaningful Error types, Result/? in docs, common trait impls, iter/into_iter conventions, and predictable public APIs."
disable-model-invocation: true
---

# Rust Coding Practices

Application skill for Rust style learning (from the archived `awesome-guidelines` style capsules). For async/concurrency or framework crates, combine with stack-specific guidance.

## Core Principle

Rust quality is **rustfmt-mechanical + API-guidelines semantic**, formatted code and public surfaces that interoperate without surprises.

## When to Use / NOT

- Rust library/application code, public API design, CI setup.
- Reviewing `Result` types, error enums, or rustdoc.

**NOT when:**

- Non-Rust code.
- Macro-heavy generated code, validate generator output, not hand-edits.

## Workflow

1. **Format & names**, `cargo fmt`, casing, conversion prefixes (`rust-style-formatting-naming.md`).
2. **Errors**, meaningful `Error + Send + Sync`, no `()`, `?` in examples (`rust-style-errors-result.md`).
3. **Interop**, common traits, `From`, iterator naming (`rust-style-traits-interop.md`).
4. **API shape**, methods, `new`, no out-params, Deref discipline, docs (`rust-style-api-predictability.md`).
5. **Verify**, `cargo fmt --check`, `cargo clippy`, `cargo test --doc`.

## Red Flags

- `Result<T, ()>`
- `unwrap()` in public docs
- `get_*` on ordinary field getters
- `Deref` on domain wrapper for `.` syntax sugar
- Manual formatting vs rustfmt
- Missing `Debug` on public types

## Verification

- `cargo fmt --check`, `cargo clippy -- -D warnings` (project policy)
- Doctests pass with `?` pattern
- Capsule checklist on public API review

## Skill Result Contract

```xml
<skill_result>
  <skill>rust-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>rs diff, fmt/clippy/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>empty error type, doc unwrap, orphan trait gap, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/rust-style-learning-note.md`
- `awesome-guidelines/references/rust-style-formatting-naming.md`
- `awesome-guidelines/references/rust-style-errors-result.md`
- `awesome-guidelines/references/rust-style-traits-interop.md`
- `awesome-guidelines/references/rust-style-api-predictability.md`
