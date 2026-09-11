<!-- capsule-v2 -->
# Concurrency and context — do goroutines and cancellation have clear lifetimes?

**Source:** Google Go decisions §Goroutine lifetimes, §Contexts; Uber §Goroutine lifecycle, §Defer. **Question:** Will shutdown cancel work and avoid leaks?

## Context seam
**Path/Symbol:** functions crossing RPC/HTTP/background boundaries.
**Signature:** `ctx context.Context` as first parameter.
**Data Shape:** no `context` stored in structs; derive from caller.

### Decisive pattern
```go
func Fetch(ctx context.Context, id string) (*Item, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, err
    }
    // ...
}

func (w *Worker) Run(ctx context.Context) error {
    var wg sync.WaitGroup
    for item := range w.q {
        wg.Add(1)
        go func() {
            defer wg.Done()
            process(ctx, item)
        }()
    }
    wg.Wait()
    return ctx.Err()
}
```

**Flow:** pass context down call chain → tie outbound requests to ctx → cancel stops work → wait for goroutines before return.
**Invariant:** never spawn a goroutine without knowing how it stops; don't store context in struct fields.
**Probe:** `go vet`/review: ctx first; shutdown tests pass; no unbounded `go func()` without WaitGroup/select.

## Globals seam
**Flow:** inject dependencies — avoid mutable package-level vars; use `sync.Once`/`Must` for init-only constants.
**Invariant:** tests and production share explicit wiring, not hidden global mutation.
**Probe:** grep mutable package vars without `_` prefix and justification comment.

## Verdict
Adopt context-first APIs, bounded goroutines, defer cleanup, no mutable globals. Learning note: `go-style-learning-note.md`.
