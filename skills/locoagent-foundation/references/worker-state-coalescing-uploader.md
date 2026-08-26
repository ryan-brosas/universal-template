<!-- capsule-v2 -->
# Coalescing state uploader — how do you PUT continuously-changing worker state with one in-flight request and no queue at all?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What merge algebra coalesces patches that arrive while a PUT is in flight or backing off, and which nulls survive?

## 1-in-flight + 1-slot pending, RFC 7396-flavored metadata merge
**Path/Symbol:** `src/cli/transports/WorkerStateUploader.ts`: `enqueue/drain/sendWithRetry` (:43-86), `coalescePatches` (:106-131).
**Signature:** `send: (body: Record<string,unknown>) => Promise<boolean>` (false = retryable failure); `enqueue(patch): void` fire-and-forget.
**Data Shape:** Exactly two slots: `inflight: Promise|null`, `pending: patch|null` — naturally bounded, hence no backpressure. Top-level keys: last value wins. `external_metadata`/`internal_metadata`: ONE-level deep overlay merge where null values are PRESERVED (server interprets them as deletes).

### Decisive source
```ts
private async sendWithRetry(payload: Record<string, unknown>): Promise<void> {
  let current = payload; let failures = 0
  while (!this.closed) {
    const ok = await this.config.send(current)
    if (ok) return
    failures++; await sleep(this.retryDelay(failures))
    // Absorb any patches that arrived during the retry
    if (this.pending && !this.closed) { current = coalescePatches(current, this.pending); this.pending = null }
  }
}
// metadata keys merge one level: overlay keys win, nulls preserved for server-side delete
merged[key] = { ...(merged[key] as Record<string, unknown>), ...(value as Record<string, unknown>) }
```

**Flow:** enqueue → coalesce into pending → kick drain if idle; drain swaps pending→in-flight; on success drains again if new pending exists; on failure loops, absorbing newer patches into the CURRENT payload before each retry.
**Invariant:** A reader never sees stale top-level fields (overlay wins) and never loses an explicit null delete inside metadata objects (spread preserves explicit null keys — do NOT "clean" them). close() nulls pending but lets the in-flight attempt finish its loop check via closed flag.
**Probe:** `grep -n "current = coalescePatches(current, this.pending)" src/cli/transports/WorkerStateUploader.ts` (`:82`), `grep -n "key === 'external_metadata' || key === 'internal_metadata'" src/cli/transports/WorkerStateUploader.ts` (`:114`), `grep -n "1 in-flight PUT + 1 pending patch" src/cli/transports/WorkerStateUploader.ts` (`:6`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "WorkerStateUploader coalescePatches RFC 7396", limit: 5 });
```

## Verdict
Adopt the two-slot shape and the null-preserving metadata merge for any last-state-wins endpoint. Adapt key names and depth (one level is deliberate). Omit absorption-during-retry only if your writers tolerate lost intermediate state.