<!-- capsule-v2 -->
# isTransientError taxonomy — which failure modes must self-heal instead of poisoning stored state, across five drivers and raw sockets?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Given any thrown error, what is the complete classification rule for "retrying on a fresh connection may succeed" — the predicate that gates whether formula columns get permanently marked invalid?

## Four-layer transient classifier (SDK types → codes → driver numbers → message phrases)

**Path/Symbol:** `packages/nocodb/src/helpers/db-error/utils.ts:isTransientError` (:40–210); enum `DBError` (:16–26); type `DBErrorExtractResult` (:3–11).
**Signature:** `isTransientError(error: any): boolean` — accepts error objects OR plain strings.
**Data Shape:** Layer 1 checks `error instanceof NcBaseErrorv2` against `[ERR_EXTERNAL_DATA_SOURCE_TIMEOUT, ERR_DATABASE_OP_FAILED]`; layers 2–3 match `error.code` (stringified) / `error.number` / `error.errorNum` / `error.isRecoverable`; layer 4 substring-matches `error.message` (or the bare string) — but ONLY when `errorMessage.length > 20`.

### Decisive source
```ts
// :96-105 — the deliberate EREQUEST omission
// MSSQL / tedious driver-level transport errors. `EREQUEST` is
// omitted intentionally — it wraps server errors that include
// permanent ones (e.g. constraint violations) where retry is wrong.
if (['ETIMEOUT', 'ESOCKET', 'EABORT', 'ECANCEL', 'EINVALIDSTATE'].includes(code)) return true;
```

**Flow:** (1) NcBaseErrorv2 with external-source-timeout or database-op-failed ⇒ transient. (2) Ten generic socket codes (ECONNREFUSED, ETIMEDOUT, ENOTFOUND, ECONNRESET, EHOSTUNREACH, EAI_AGAIN, EPIPE, ENETUNREACH, ECONNABORTED, EHOSTDOWN). (3) Per-driver: PG class-08 prefix + 57014/57P01/57P02/57P03 + 53300; MySQL ER_LOCK_WAIT_TIMEOUT/ER_CON_COUNT_ERROR/ER_TOO_MANY_USER_CONNECTIONS/ER_CONNECTION_COUNT_ERROR/CR_CONNECTION_ERROR/CR_CONN_HOST_ERROR; SQLite SQLITE_BUSY/SQLITE_LOCKED; MSSQL tedious list MINUS EREQUEST; filesystem EACCES/EROFS/ENOSPC; Oracle NJS-500/501/503/510/511/518/521 plus a 16-entry ORA- number set (18, 28, 54, 60, 1033, 1034, 2049, 3113, 3114, 4021, 30006, 12170, 12514, 12537, 12541) parsed via `/^ORA-(\d+)$/`; node-oracledb `isRecoverable === true`; MSSQL server `number` in {952, 1205, 1222, 3960, 40197, 40501, 40613, 49918, 49919, 49920}. (4) Sixteen connection phrases ('connection refused', 'database is locked', 'timeout acquiring a connection', …) under the >20-char guard.
**Invariant:** (1) This is the SAME predicate consumed by the formula dry-run latch (see formula-dryrun-transient-doctrine) — a porter who makes it too permissive turns permanent validation failures into unmarked silent breakage; too strict and an unreachable external source bricks every formula column. (2) EREQUEST must stay EXCLUDED: it wraps server-side permanent errors. (3) The message-phrase layer is deliberately last and length-guarded to avoid false positives on short generic messages.

### Porting traps (each verified against source)
- Oracle transient detection needs THREE shapes: NJS driver codes, the ORA-number allowlist, AND `isRecoverable` flag (:110–156) — porting only one shape misses startup-window failures like NJS-518 ("service not registered", fires while DB/PDB starts).
- In-file anchors: `grep -c "code.startsWith('08')" src/helpers/db-error/utils.ts` → 1; `grep -c "'NJS-518'" …` → 2 (comment + entry); `grep -c "isRecoverable === true" …` → 1; `grep -n 'errorMessage.length > 20' …` → :185.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'EREQUEST' src/helpers/db-error/utils.ts | head -2` → hits at :97/:100 region (comment + omission list WITHOUT EREQUEST) and `sed -n '99,105p' src/helpers/db-error/utils.ts | grep -c EREQUEST` → `0`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "isTransientError transient connection error classification", limit: 10 });
```
Resolves `isTransientError` in `db-error/utils.ts` rank-1 group.

## Verdict
Adopt the four-layer order (typed SDK errors first, phrases last) verbatim including the EREQUEST hole; adapt code sets when adding drivers; omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
