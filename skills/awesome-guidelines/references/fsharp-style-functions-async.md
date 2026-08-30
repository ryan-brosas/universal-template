<!-- capsule-v2 -->
# Functions and async — are signatures idiomatic for the intended consumer?

**Source:** Microsoft guidelines §Function signatures, Extension Members, Inline constraints. **Question:** Are async, returns, and extensions shaped for F# callers?

## Signature seam
**Path/Symbol:** public members on F#-facing library types.
**Signature:** `Async<'T>` at F# boundaries; named types over large tuples.
**Data Shape:** extension members on BCL types for idioms.

### Decisive pattern
```fsharp
type DataService() =
    member _.Load(id: int) : Async<Result<Data, exn>> =
        async {
            let! raw = fetchRaw id
            return parse raw
        }

type System.Collections.Generic.IDictionary<'Key, 'Value> with
    member dict.TryGet key =
        match dict.TryGetValue key with
        | true, v -> Some v
        | false, _ -> None
```

**Flow:** synchronous `Operation` paired with `AsyncOperation` or `OperationAsync` returning `Async<_>`/`Task<_>` as appropriate → small unrelated multi-values may use tuples; related components use named record/type → add extension members only for intrinsic BCL idioms (`TryGet`, `AsyncReceive`) → reserve inline + member constraints for math/numeric public APIs only — avoid duck-typing constraints on general libraries.
**Invariant:** heavy SRTP constraints on consumer-facing API, or `Task` without cancellation on long vanilla .NET methods, fails review.
**Probe:** signature file / reflected API check; constraint count on exported inline functions.

## Type alias seam
**Flow:** avoid public abbreviations that change expected member semantics — wrap in class or single-case DU instead of `type MultiMap = Map<_, list>` leaking Map operators.
**Invariant:** public type alias with incompatible dot-notation semantics fails review.
**Probe:** API design review against underlying type operations.

## Verdict
Async naming, purposeful extensions, restrained constraints, no leaky abbreviations. Learning note: `fsharp-style-learning-note.md`.
