---
title: go-coding-practices
summary: Use when reviewing Go formatting, error handling, API boundaries, or goroutine lifetimes; apply project conventions and distinguish ordinary errors from invariant failures.
kind: playbook
---

# Go Coding Practices

Application skill for Go style. For service layout or framework patterns, follow project conventions and the framework's own source or docs.

## Core Principle

Go code should be **gofmt-clear, error-explicit, and concurrency-obvious**, interfaces earned at the consumer, not invented at the producer.

## When to Use / NOT

- Writing or reviewing Go packages, CLIs, or services.
- Setting up `gofmt`, `go vet`, `staticcheck` in CI.

**NOT when:**

- Non-Go code.
- Generated protobuf/grpc stubs, validate generators, not hand-edits.

## Workflow

1. **Format & names**, gofmt, MixedCaps, context-aware locals.
2. **Errors**, ordinary failures usually return `error`; preserve the project
   policy for panic/recover at invariant or framework boundaries.
3. **APIs**, concrete returns, small consumer interfaces, named external literals.
4. **Concurrency**, make goroutine lifetime, cancellation, and synchronization
   explicit. Use context where needed; assess shared mutable state rather than
   banning every global.
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
