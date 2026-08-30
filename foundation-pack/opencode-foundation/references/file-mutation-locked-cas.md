<!-- capsule-v2 -->
# FileMutation locked write ladder — per-canonical-path serialization with compare-and-swap

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do you serialize cooperating file mutations so a conditional write's read-compare-write window cannot interleave with another writer?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/file-mutation.ts`: `withTargetLock` (:62-64), `write` (:66-74), `writeTextPreservingBom` (:76-90), `create` (:92-110), `writeIfUnchanged` (:112-124), `remove` (:126-135).
**Signature:** `Interface = {create, write, writeTextPreservingBom, writeIfUnchanged, remove}` over `Target = {canonical: string, resource: string}`; errors: `TargetExistsError`, `StaleContentError`, `FSUtil.Error`.
**Data Shape:** `KeyedMutex.makeUnsafe<string>()` registry keyed by `target.canonical`; every op body wrapped `Effect.uninterruptible` inside the lock; results carry `{operation, target, resource, existed}`.

### Decisive source
```ts
const withTargetLock =
  (target: Target) =>
  <A, E, R>(effect: Effect.Effect<A, E, R>) =>
    locks.withLock(target.canonical)(Effect.uninterruptible(effect))
...
const writeIfUnchanged = Effect.fn("FileMutation.writeIfUnchanged")((input: ConditionalWriteInput) =>
  withTargetLock(input.target)(
    Effect.gen(function* () {
      const current = yield* fs.readFile(input.target.canonical)
      if (!sameBytes(current, input.expected)) {
        return yield* new StaleContentError({ path: input.target.canonical })
      }
      yield* ...write...
```

**Flow:** resolve the target through LocationMutation first (canonical + resource) → every mutation takes the per-canonical-path lock → `create` uses the `wx` flag so a target that appears after resolution fails with `TargetExistsError` (and a target that disappears after resolution is created via the mkdir-on-NotFound retry); `write` reports pre-write existence; `writeTextPreservingBom` reads the current file INSIDE the lock and preserves its UTF-8 BOM while emitting at most one (split/join on `\uFEFF`); `writeIfUnchanged` reads + `sameBytes` + writes inside the SAME lock window (process-local CAS); `remove` maps NotFound to `existed: false` without a pre-check.
**Invariant:** the compare in a conditional write happens under the same lock as the write — no cooperating writer can slip a change between read and write; distinct canonical targets never block each other (KeyedMutex per-key independence); mutation bodies are uninterruptible so a cancelled fiber cannot release the lock mid-write.
**Probe:** `packages/core/test/file-mutation.test.ts` (13 it.live: BOM preservation/normalization, create-after-appear → TargetExistsError with "winner" intact, create-after-disappear succeeds, serialization of concurrent writes to one canonical target via instrumented FSUtil Deferred handshakes, only one concurrent conditional write wins + loser gets StaleContentError, distinct targets proceed independently).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "FileMutation writeIfUnchanged withTargetLock KeyedMutex uninterruptible", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-canonical-path keyed serialization with uninterruptible bodies for any tool-driven file-edit service; adopt in-lock compare-and-swap instead of optimistic rename dances when all writers cooperate in-process. Adapt Target resolution to your host's path-canonicalization layer. Omit the BOM preservation if your editor surface is byte-exact already. Coverage caveat: Codebase Memory MCP not connected this pass — source+test reading fallback per AGENTS.md.
