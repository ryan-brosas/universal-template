<!-- capsule-v2 -->
# POSIX file-ops hardening kit — what transient-failure classes must a portable agent harness retry, and how do you tail a huge JSONL log without reading it whole?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** which rename/rm/atomicity pitfalls recur across platforms here, and what is the shared backward-pagination contract?

## Four small primitives: atomic write, rename retry, rm retry, reverse JSONL pager
**Path/Symbol:** `src/core/atomic-write.ts` (:18 RETRYABLE_RENAME_CODES, :39-58 `renameAtomic`, :60-80 `writeFileAtomic`); `src/agents/rm.ts:22-40` (`removeTree`); `src/log-tail.ts:51-125` (`readJsonlPage*`); pattern instance of the pid-liveness probe: `src/agents/transports/process-utils.ts:46-54` (`processIsAlive`) — same 4-line shape recurs at `src/residency/host.ts:51-59`, `src/actors/manager.ts:1710-1718`.
**Signature:** `writeJsonAtomic(path, value, {mode?=0o600, dirMode?=0o700, space?, newline?, renameRetries?=8, renameRetryDelayMs?=25})`; `renameAtomic(source, target, options?)`; `removeTree(target, rm?)`; `readJsonlPage(filePath, limit, before?, maxBytes?): {lines, hasMore, before?}`.
**Data Shape:** rename retries on {EPERM,EACCES,EEXIST,EBUSY} with linear 25ms backoff (Windows AV/indexer contention); rm retries on {ENOTEMPTY,EBUSY,EPERM,EMFILE} ×5; pager caps reads at 8MB and returns byte offsets as stable older-page cursors.

### Decisive source
```ts
// Windows: milliseconds of contention, not a policy failure → bounded retry
if (attempt === attempts || code === undefined || !RETRYABLE_RENAME_CODES.has(code)) throw error;
syncSleep(delay * attempt);            // Atomics.wait legal on the Node main thread
// temp name carries pid+uuid so concurrent writers never collide:
const temporary = `${filePath}.${process.pid}.${randomUUID()}.tmp`;
// backward page: stop conditions are line-count AND byte-budget; first partial
// chunk's leading fragment is dropped unless bufferStart===0 (file head)
```

**Flow:** every durable state write goes temp→rename with parent mkdir at 0700 and commit at 0600; cleanup paths wrap `fs.rm` in the retry ladder so APFS ENOTEMPTY races don't flake shutdown; log readers (`agents.readLog`, actor logs) request pages by count, get back complete records only (malformed lines preserved as `{offset, raw}`), plus `hasMore` + exact `before` offset for the next page.
**Invariant:** the pid-liveness probe MUST treat non-positive/non-safe integers as dead and swallow EPERM (process exists but is owned by another user ⇒ alive for our purposes only when kill(0) succeeds); pagination cursors are byte offsets captured from the FIRST record of the returned page — recomputing them from line counts breaks once files contain malformed rows.
**Probe:** `tests/log-tail.test.ts:14` ("bounded tail pages with stable older-page cursors"), :43 (page beginning beyond final chunk), :76 (malformed lines kept raw); `tests/agent-rm.test.ts:16,34` (retry then succeed; rethrow non-retryable). No dedicated atomic-write suite — behavior exercised transitively via actor/residency tests; caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "writeJsonAtomic removeTree readJsonlPage processIsAlive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four primitives verbatim for cross-platform agent infrastructure; adapt error-code sets to your target platforms; omit Atomics.wait fallback if you never sleep synchronously. Direct tests cover pager + rm; atomic-write carries an indirect-only coverage caveat.
