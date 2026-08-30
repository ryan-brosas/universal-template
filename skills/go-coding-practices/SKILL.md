---
name: go-coding-practices
description: "Use when authoring or reviewing Go, gofmt, MixedCaps naming, explicit error returns, early error flow, consumer-defined interfaces, context-first APIs, goroutine lifetimes, and no production panic."
disable-model-invocation: true
---

# Go Coding Practices

Application skill for Go style learning (from the archived `awesome-guidelines` style capsules). For service layout or framework patterns, follow project conventions and stack capsules in `foundation-pack/`.

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
2. **Errors**, `(T, error)`, early return, wrap, defer, no prod panic (`go-style-errors-flow.md`).
3. **APIs**, concrete returns, small consumer interfaces, named external literals (`go-style-interfaces-apis.md`).
4. **Concurrency**, `ctx` first, bounded goroutines, no mutable globals (`go-style-concurrency-context.md`).
5. **Verify**, `go test`, `go vet`, staticcheck on changed packages.

## Red Flags

- `panic` in library handlers
- Ignored `err` without comment
- Exported mega-interfaces for "clean architecture"
- `go func()` with no shutdown
- Snake_case or skipping gofmt
- Positional struct literal for imported types

## Verification

- `gofmt -l` clean; `go vet ./...`; project staticcheck/golangci-lint
- Tests include error paths; shutdown/cancel tests for workers
- Capsule checklist on review

## Skill Result Contract

```xml
<skill_result>
  <skill>go-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>go diff, test/vet/lint output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>panic path, goroutine leak, ignored err, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/go-style-learning-note.md`
- `awesome-guidelines/references/go-style-formatting-naming.md`
- `awesome-guidelines/references/go-style-errors-flow.md`
- `awesome-guidelines/references/go-style-interfaces-apis.md`
- `awesome-guidelines/references/go-style-concurrency-context.md`
