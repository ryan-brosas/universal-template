<!-- capsule-v2 -->
# Durable-payload JSON gate — what must be rejected BEFORE a session write, not after?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c`; Codebase Memory `pi-upstream`. **Question:** A porter validates durable payloads with `JSON.parse(JSON.stringify(x))` round-tripping — what does that miss, and where is the gate enforced?

## assertJsonSerializable: strict structural whitelist at every commit boundary
**Path/Symbol:** `packages/agent/src/harness/session/session.ts:41-100` (`assertJsonSerializable`), call sites :286-289 (`commitEntry`), :291-298 (`commitRecord`), `packages/agent/src/harness/session/jsonl/repo.ts:208` (header metadata).
**Signature:** `export function assertJsonSerializable(value: unknown): void` — throws `SessionError("invalid_payload", ...)` on first violation; iteratively walks with an explicit stack plus a `WeakSet` cycle guard.
**Data Shape:** Accepts null/string/boolean/finite number/plain objects/arrays only. Rejects: non-finite numbers (`NaN`/`±Infinity`, which JSON.stringify silently turns into `null`), any non-object non-primitive (`function`, `symbol`, `bigint`, `undefined`), reference cycles, non-plain prototypes (class instances), symbol-keyed properties, accessor properties (getters — value could change between check and encode), sparse arrays, arrays with extra own properties, non-standard-array prototypes.

### Decisive source
```ts
if (typeof candidate === "number") {
    if (!Number.isFinite(candidate)) invalidPayload("contains a non-finite number");
    continue;
}
...
if (active.has(candidate)) invalidPayload("contains a cycle");
...
if (
    Object.getOwnPropertySymbols(candidate).length > 0 ||
    Object.getOwnPropertyNames(candidate).length !== candidate.length + 1
) {
    invalidPayload("contains an array with unsupported properties");
}
for (let index = candidate.length - 1; index >= 0; index--) {
    if (!Object.hasOwn(candidate, index)) invalidPayload("contains a sparse array");
```

**Flow:** Session facade calls the gate inside `commitEntry`/`commitRecord` before handing to ANY storage backend (memory or JSONL alike), and the JSONL repo gates header metadata at create time. So the invariant holds at the API boundary once, not per-backend.
**Invariant:** Everything that reaches the log must survive a lossless JSON round-trip *and* keep its shape — because a torn-tail loader replays these lines and the seq/lane validation assumes decoded values equal written values. Round-trip testing misses cycles (stack overflow instead of clean error), accessors/symbols (silently dropped), class instances (prototype lost), and non-finite numbers (coerced to null) — all four corrupt replay.
**Probe:** No dedicated unit file for the validator itself at this pin (coverage caveat); behavior is pinned transitively by the storage conformance harness `packages/agent/src/harness/session/testing/conformance.ts` (every case writes through `repository.create/append*`) and the JSONL persistence suite `packages/agent/test/harness/session/jsonl.test.ts` ("writes one line per mutation and restores the shared sequence" :267).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "assertJsonSerializable durable payload", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves `session.ts:41-100` rank #1.)

## Verdict
Adopt gate-at-the-boundary: validate payloads once in the facade before any backend sees them, rejecting non-finite numbers, cycles, prototypes, symbols, accessors, and sparse/non-standard arrays. Adapt the rejection list to your codec. Omit nothing if your log is replay-based — this gate is what makes load-time triage trustworthy. Coverage caveat: validator lacks a direct unit suite; rely on conformance coverage or add your own.
