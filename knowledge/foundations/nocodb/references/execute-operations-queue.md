<!-- capsule-v2 -->
# executeOperations queue — what concurrency and failure semantics bound every bulk metadata write?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does NcHelp.executeOperations guarantee to callers that enqueue hundreds of per-table insert closures?

## executeOperations queue
**Path/Symbol:** `packages/nocodb/src/utils/NcHelp.ts` — `executeOperations` (:11–41), concurrency constant (:5–7).
**Signature:** `executeOperations(fns: Array<() => Promise<any>>, _dbType: string): Promise<any>` — resolves with the FIRST captured error thrown, else undefined.
**Data Shape:** PQueue with `NC_EXECUTE_OPERATIONS_CONCURRENCY` (parseInt of env || 5); local `errors: []`.

### Decisive source
```ts
// :20–40:
for (const fn of fns) {
  queue.add(async () => {
    if (errors.length) {
      return;            // late tasks no-op once any error exists
    }
    try {
      await fn();
    } catch (e) {
      this.logger.error(e);
      errors.push(e);
    }
  });
}
await queue.onIdle();
if (errors.length) {
  throw errors[0];       // exactly the first error surfaces
}
```

**Flow:** all closures are enqueued immediately → up to 5 run concurrently → after a failure, ALREADY-QUEUED closures still dequeue but return instantly (skipped, not executed) → when the queue drains, the first error is rethrown to the caller.
**Invariant:** (1) Failure is fail-fast-with-drain: in-flight and queued tasks don't pile more errors; exactly errors[0] propagates. (2) The `_dbType` parameter is UNUSED (underscore-prefixed) — dialect-specific behavior lives inside the closures. (3) Callers must not assume task completion order matches array order beyond concurrency-5 batching.
**Probe:** `grep -c "if (errors.length)" packages/nocodb/src/utils/NcHelp.ts` → `2`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "executeOperations PQueue onIdle", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bounded-concurrency + skip-after-first-error + rethrow-first semantics as the canonical bulk-meta write primitive; adapt PQueue to host equivalent; omit the vestigial dbType param.
