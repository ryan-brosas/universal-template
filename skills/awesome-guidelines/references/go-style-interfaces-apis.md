<!-- capsule-v2 -->
# Interfaces and API shapes — are abstractions earned and literals safe?

**Source:** Google Go decisions §Interfaces, §Pass values, §Literal formatting; Effective Go §Interfaces. **Question:** Will callers get concrete power without unnecessary interfaces?

## Interface seam
**Path/Symbol:** exported APIs and test doubles.
**Signature:** small consumer-defined interfaces; functions accept interfaces, return concrete.
**Data Shape:** `-er` names for single-method interfaces (`io.Reader`).

### Decisive guidance
```go
// Consumer defines what it needs
type storage interface {
    Get(ctx context.Context, key string) ([]byte, error)
}

func NewIndexer(store storage) *Indexer { ... }

// Return concrete *Indexer, not interface
func NewIndexer(cfg Config) (*Indexer, error) { ... }
```

**Flow:** start with concrete types → extract interface at **call site** when multiple implementations exist → keep interfaces minimal and documented.
**Invariant:** don't export interfaces solely for mocking; don't wrap RPC clients in manual interfaces for tests.
**Probe:** exported interface count justified; no `*io.Reader` or `*interface` parameter tricks.

## Literals & pointers seam
```go
r := csv.Reader{
    Comma:           ',',
    FieldsPerRecord: 4,
}
```

**Flow:** external struct literals **must** use field names → omit zero values when clear → pass protobuf/large structs by pointer.
**Invariant:** positional struct literals forbidden for cross-package types — coupling to field order.
**Probe:** vet/staticcheck on struct literals; pointer receiver choice matches mutation/size rules.

## Verdict
Adopt consumer-defined small interfaces, concrete returns, named field literals. Learning note: `go-style-learning-note.md`.
