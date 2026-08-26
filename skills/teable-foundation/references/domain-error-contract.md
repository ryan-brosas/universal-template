<!-- capsule-v2 -->
# Result-style domain errors — how do you make failures serializable, typed, and translatable to HTTP without throwing across layers?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the error-data contract that every v2 handler/adapter shares, and how do tags drive status mapping?

## Frozen data-object errors on neverthrow Result rails
**Path/Symbol:** `packages/v2/core/src/domain/shared/DomainError.ts`: tag vocabulary `domainErrorTagValues` (36–47), contract `interface DomainError` (78–86), frozen factory `createError` (105–111); factories used everywhere as `domainError.notFound({code, message})`, `.validation`, `.conflict`, `.invariant`, `.unauthorized`, `.forbidden`, `.infrastructure`, `.unexpected`; HTTP translation `apps/nestjs-backend/src/custom.exception.ts:getDefaultCodeByStatus` (22–51).
**Signature:** `interface DomainError { readonly code: string /* dot-namespaced, e.g. "record.not_found" */; readonly message: string; readonly tags: ReadonlyArray<'validation'|'conflict'|'not-found'|'invariant'|'not-implemented'|'unauthorized'|'forbidden'|'infrastructure'|'unexpected'>; readonly details?: Readonly<Record<string, unknown>>; toString(): string }`.
**Data Shape:** plain frozen object — deliberately NOT an Error subclass so it survives RPC/queue boundaries and structuredClone; every fallible API returns `Result<T, DomainError>` (neverthrow) or generator-delegates via `safeTry`.

### Decisive source
```ts
// Design decisions (verbatim from the header):
// - Plain data object (not extending Error) to remain serializable across boundaries.
// - No throw/exception semantics; errors are returned via Result<T, DomainError>.
// - Immutable (all fields readonly) for predictable behavior.
export interface DomainError {
  readonly code: DomainErrorCode;      // "validation.field.name_empty" convention
  readonly message: string;
  readonly tags: ReadonlyArray<DomainErrorTag>;  // primary tag first, deduped by factory helper
  readonly details?: Readonly<Record<string, unknown>>;
  toString(): string;
}
```

**Flow:** domain/repo code returns `err(domainError.notFound({…}))` → callers propagate with `yield*` inside `safeTry` generators (no try/catch ladders) → at the edge, ONE mapper turns tags into HTTP statuses (`validation→400, unauthorized→401, forbidden→403, not-found→404, conflict→409, infrastructure/unexpected→500`) and codes into stable machine codes. Infrastructure retries consult tags: the UoW retry gate requires `tags.includes('infrastructure')` plus a deadlock/serialization message match (see unit-of-work capsule).
**Invariant:** the domain NEVER throws for expected failure — a thrown error is by definition `unexpected`; the primary tag is always present and deduplicated by the factory helper; codes are dot-namespaced strings so new codes are additive, never breaking.
**Probe:** `packages/v2/core/src/domain/shared/DomainBasics.spec.ts::"creates valid ids and rejects invalid values"` (:50) pins the shared-domain basics suite; HTTP-side mapping pinned by `apps/nestjs-backend/src/configs/config.spec.ts` sibling coverage of `custom.exception.ts`. Honest caveat: no dedicated upstream spec file for DomainError factories themselves — port with your own table test over the nine tags.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "domainError DomainError safeTry", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the nine-tag taxonomy + frozen-plain-object + Result-rails discipline as a package-wide contract — it is what makes teable's handlers compose without exception plumbing. Adapt tag names/status table to host conventions. Omit nothing here; this is the cheapest capsule in the pack. Caveat: direct factory tests absent upstream (noted in Probe).
