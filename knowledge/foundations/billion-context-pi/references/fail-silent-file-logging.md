<!-- capsule-v2 -->
# Fail-silent file logger — how does diagnostic logging never crash the host while keeping errors always-on and debug opt-in?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** How must an extension's logger write structured lines to a shared file so that logging failures, oversized files, and debug gating can never take down the session?

## writeLine: every I/O step individually swallowed; rotation before append
**Path/Symbol:** `src/log.ts` (105L, whole): `writeLine` (:39-56), `resolveLogFile` (:11-13), `debugOn` (:21-23), `logThrow` (:75-84), `logger` facade (:98-105).
**Signature:** `writeLine(level, scope, fields: Record<string, unknown>) -> void`; `logThrow(scope, err, extra?) -> never-returns-but-logs` (callers re-throw after); `setDebugEnabled(bool)` overrides env `ACP_DEBUG=1|true`.
**Data Shape:** line = `<ISO ts> [<level>] [<scope>] k1=v1 k2=v2\n`; values stringified via `fmt` (string as-is; Error → stack||String; JSON with String() fallback); destination `$ACP_LOG_FILE` or `~/<CONFIG_DIR>/acp.log`.

### Decisive source
```ts
// src/log.ts:41-55 — three separate try/catch: NOTHING in this function throws
try {
  if (existsSync(file) && statSync(file).size >= MAX_BYTES) {
    renameSync(file, file + ".old");       // 10 MiB single-generation rotate
  }
} catch {}
...
try {
  mkdirSync(path.dirname(file), { recursive: true });
  appendFileSync(file, line);
} catch {}
```

**Flow:** resolve path per call (env changes honored without restart) → rotate if ≥10 MiB by rename to `.old` (one generation only — old logs are disposable diagnostics) → format fields as `k=v` pairs → mkdir+append. Levels error/warn/info ALWAYS write; `debug.event` writes only when runtime `setDebugEnabled` or env opted in. The `closeLogStream()` export is a deliberate no-op kept for API symmetry with a stream-based implementation. Callers pair `logThrow(scope, e)` with a re-throw so hosts render the failure while the log keeps forensic fields (sid/query/phase).
**Invariant:** (1) logging is fail-silent BY DESIGN — every fs step is independently guarded because a diagnostic layer that can throw becomes a new failure surface inside error handlers (re-entrancy hazard: logError called FROM a catch block); (2) debug is strictly opt-in at one of exactly two gates (env at module load, runtime override), and its OFF state means the file may not exist at all (tests assert empty-string-on-ENOENT); (3) rotation renames rather than truncates so a concurrent reader never sees a half-file.
**Probe:** `tests/log.test.ts:19` ("error/warn/info are written when debug is OFF (always-on)"), `:34` ("debug.event is NOT written when debug is OFF" incl. ENOENT→"" tolerance), `:48` (ON case), `:59` (logThrow records message+stack as error), `:85` ("rotation renames oversized file to .old").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "logThrow writeLine resolveLogFile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-silent-per-step structure and always-on-errors/debug-opt-in split for any extension logger. Adapt the size threshold and field format to your platform. Omit the no-op closeLogStream unless you mirror the API for swap-in stream implementations.
