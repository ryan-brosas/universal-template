---
name: go-coding-practices
description: "Use when reviewing Go formatting, error handling, API boundaries, or goroutine lifetimes; apply project conventions and distinguish ordinary errors from invariant failures."
invocation: manual
disable-model-invocation: true
---

# Go Coding Practices

Application skill for Go style learning (from the archived `awesome-guidelines` style capsules). For service layout or framework patterns, follow project conventions and stack capsules in `skills/*-foundation`.

## Core Principle

Go code should be **gofmt-clear, error-explicit, and concurrency-obvious**, interfaces earned at the consumer, not invented at the producer.

## When to Use / NOT

- Writing or reviewing Go packages, CLIs, or services.
- Setting up `gofmt`, `go vet`, `staticcheck` in CI.

**NOT when:**

- Non-Go code.
- Generated protobuf/grpc stubs, validate generators, not hand-edits.

## Workflow

1. **Format & names**, gofmt, MixedCaps, context-aware locals (`go-style-formatting-naming.md`).
2. **Errors**, ordinary failures usually return `error`; preserve the project
   policy for panic/recover at invariant or framework boundaries. Consult
   `go-style-errors-flow.md` for source-specific options.
3. **APIs**, concrete returns, small consumer interfaces, named external literals (`go-style-interfaces-apis.md`).
4. **Concurrency**, make goroutine lifetime, cancellation, and synchronization
   explicit. Use context where needed; assess shared mutable state rather than
   banning every global (`go-style-concurrency-context.md`).
5. **Verify**, use the project's test/vet/lint commands on changed packages;
   additional tools are options, not automatic setup work.

## Red Flags

- Ordinary recoverable failures unexpectedly escaping as panics
- Ignored `err` without comment
- Exported mega-interfaces for "clean architecture"
- `go func()` with no shutdown
- Snake_case or skipping gofmt
- Positional struct literal for imported types

## Verification

- `gofmt -l` clean; `go vet ./...`; project staticcheck/golangci-lint
- Tests include error paths; shutdown/cancel tests for workers
- Capsule checklist on review


## References

- `awesome-guidelines/references/go-style-learning-note.md`
- `awesome-guidelines/references/go-style-formatting-naming.md`
- `awesome-guidelines/references/go-style-errors-flow.md`
- `awesome-guidelines/references/go-style-interfaces-apis.md`
- `awesome-guidelines/references/go-style-concurrency-context.md`
