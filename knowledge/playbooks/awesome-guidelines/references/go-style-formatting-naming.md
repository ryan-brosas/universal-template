<!-- capsule-v2 -->
# Formatting and naming — does code match gofmt and Go naming idioms?

**Source:** Google Go guide §Formatting, §MixedCaps, §Naming; Effective Go §Names. **Question:** Will `go fmt` and idiomatic names keep diffs readable?

## Format seam
**Path/Symbol:** `*.go` source files.
**Signature:** `gofmt`-canonical layout; tabs for indent (gofmt default).
**Data Shape:** camel case identifiers; no snake_case.

### Decisive rules
```go
const MaxPacketSize = 512 // exported MixedCaps

type HTTPServer struct{}

func (s *HTTPServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {}

func userCount(db *DB) (int, error) { ... }
```

**Flow:** write idiomatic Go → run `gofmt`/`go fmt` → prefer refactor over arbitrary line breaks.
**Invariant:** **all** Go source passes gofmt in CI; multi-word names use camel case, not underscores.
**Probe:** `gofmt -l` empty on changed files; no `snake_case` identifiers in new code.

## Naming seam
**Flow:** shorten locals using context — inside `UserCount()`, prefer `count` over `userCount`; receiver names consistent (`db *DB` → `db`).
**Invariant:** names encode **what** at point of use, not origin field path; avoid stutter (`db.DBLoad` → `db.Load`).
**Probe:** review flags redundant type prefixes on locals; initialisms like `URL`, `ID` cased correctly.

## Verdict
Adopt gofmt + MixedCaps + context-aware short names. Learning note: `go-style-learning-note.md`.
