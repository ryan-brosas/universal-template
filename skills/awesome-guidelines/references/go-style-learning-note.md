# Go style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `go-style-*.md` capsules, `go-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google Go Style Guide](https://google.github.io/styleguide/go/guide) + [decisions](https://google.github.io/styleguide/go/decisions) | Clarity/simplicity principles; `gofmt`; MixedCaps; error-last returns; indent error flow; no production panic; consumer-defined interfaces; context first; goroutine lifetimes; struct literal field names |
| [Effective Go](https://go.dev/doc/effective_go) | Multiple returns for errors; `if err := …; err != nil`; defer cleanup; comma-ok; small interfaces (`-er` suffix); accept interfaces at API boundary |
| [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md) | Don't panic in production; defer for cleanup; avoid mutable globals; goroutine lifecycle; no `*interface` |

**Not duplicated here:** Standard project layout (directory scaffolding) — adopt per repo; not a style invariant. RPC/framework specifics — use stack capsules in `foundation-pack/`.

## Mental model

Go style optimizes for **reader clarity at maintenance time**:

1. **Mechanical format** — `gofmt` is law; camel case (`MixedCaps`), not snake_case.
2. **Explicit errors** — `(T, error)` with `error` last; handle/return/wrap; early returns; no in-band `-1`/nil sentinel APIs in new code.
3. **Small surfaces** — interfaces when needed (consumer defines); return concrete types; avoid premature abstraction/generics.
4. **Obvious concurrency** — `context.Context` first parameter; know how every goroutine stops; `defer` for cleanup.
5. **Least mechanism** — maps/slices/channels before new deps; complexity only with comments/tests explaining why.

## Decision tables

### Formatting & naming

| Topic | Rule |
|---|---|
| Format | `gofmt` / `go fmt` mandatory |
| Names | `MixedCaps` / `mixedCaps`; no snake_case |
| Line length | no fixed max — refactor first |
| Receivers | 1–2 letter abbrev of type; consistent within type |
| Repetition | drop redundant package/type prefix in locals (`UserCount` → `count`) |
| Initialisms | `HTTPServer`, `userID` (ID caps in acronyms) |

### Errors

| Case | Rule |
|---|---|
| Signature | `func F() (T, error)` — error last |
| Success | `return v, nil` |
| Strings | lowercase, no trailing `.` |
| Handling | handle, return, or log.Fatal at startup — not `_` without comment |
| Flow | guard clauses; happy path not nested |
| Panic | init/`Must*` only; production returns `error` |
| Concrete nil | don't return `*os.PathError` concrete nil as error interface |

### APIs & types

| Case | Rule |
|---|---|
| Interfaces | define at consumer; keep small; avoid RPC wrapper interfaces for testing |
| Returns | prefer concrete types; accept interfaces as params |
| Struct literals | field names required for external types |
| Pointers | don't pass `*string`/`*io.Reader` to save bytes; protobuf by pointer |
| Context | `ctx context.Context` first param; no ctx in structs |

### Concurrency

| Case | Rule |
|---|---|
| Goroutines | document exit; `WaitGroup`/context cancel |
| defer | close files, unlock mutexes |
| Channels | don't send on closed channel |
| Globals | avoid mutable package globals |

## Anti-patterns

- `panic("invalid arg")` in library/production path
- `_ = do()` without comment on ignored error
- `type Service interface { …20 methods… }` at producer
- `go process(item)` with no shutdown story
- `return (*PathError)(nil)` wrapped as non-nil error
- Snake_case identifiers
- Struct literal without field names for imported types

## Skill trace

| Artifact | Role |
|---|---|
| `go-style-formatting-naming.md` | gofmt, MixedCaps, names |
| `go-style-errors-flow.md` | errors, panic, defer basics |
| `go-style-interfaces-apis.md` | interfaces, literals, pointers |
| `go-style-concurrency-context.md` | context, goroutines, globals |
| `go-coding-practices` | application skill |
