<!-- capsule-v2 -->
# Session-scoped debug logging — AsyncLocalStorage context, sanitized per-session NDJSON, fail-open silence

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you give fire-and-forget background workers structured, session-partitioned diagnostics without threading a logger through every call?

## Ambient context (`src/debug-log.ts`)
**Path/Symbol:** `debug-log.ts:18-23` (`storage`, `withDebugLogContext`), `debug-log.ts:25-41` (`safeDebugLogSessionId`, `debugLogRelativePath`), `debug-log.ts:43-64` (`debugLog`), `debug-log.ts:66-72` (`rotateIfNeeded`).
**Signature:** `withDebugLogContext<T>(context: DebugLogContext, fn: () => T): T`; `debugLog(event: string, data?: Record<string, unknown>): void`.
**Data Shape:** context = `{ enabled, cwd?, sessionId?, sessionFile?, runId? }`; each line = `{ ts, event, cwd, sessionId, sessionFile, runId, data }` NDJSON.

### Decisive source
```ts
const storage = new AsyncLocalStorage<DebugLogContext>();

export function withDebugLogContext<T>(context: DebugLogContext, fn: () => T): T {
	const parent = storage.getStore();
	return storage.run({ ...parent, ...context }, fn);      // MERGE over parent, not replace
}

export function safeDebugLogSessionId(sessionId: string | undefined): string | undefined {
	const trimmed = sessionId?.trim();
	if (!trimmed) return undefined;
	const sanitized = trimmed
		.replace(/[^A-Za-z0-9._-]+/g, "_")
		.replace(/^_+|_+$/g, "")
		.slice(0, 128);
	if (!/[A-Za-z0-9]/.test(sanitized)) return undefined;   // "---" ⇒ unusable ⇒ legacy path
	return sanitized;
}

export function debugLog(event: string, data = {}): void {
	const context = storage.getStore();
	if (context?.enabled !== true) return;                   // disabled = zero cost
	try {
		const path = join(getAgentDir(), debugLogRelativePath(context));
		mkdirSync(dirname(path), { recursive: true });
		rotateIfNeeded(path);                                // >10MB ⇒ rename to .1 (unlink old .1)
		appendFileSync(path, `${JSON.stringify(payload)}\n`, "utf-8");
	} catch {
		// Debug logging must never affect memory behavior.
	}
}
```

**Flow:** the consolidation pipeline wraps its whole run in `withDebugLogContext({ enabled: config.debugLog, cwd, ...sessionMetadata, runId }, …)` (`consolidation-trigger.ts:177-184`); every stage then calls bare `debugLog("observer.start", …)` with NO logger argument — AsyncLocalStorage propagates the context across awaits inside the async task; stream failures surface via `logAgentStreamError(stage, event)` writing `{stage}.stream_error` (`stream-errors.ts:13-22`) because agent-loop errors arrive as normal events with `stopReason:"error"`, not exceptions.
**Invariant:** The log write is wrapped in try/catch that SWALLOWS EVERYTHING — diagnostics must never alter memory behavior. Path is derived from a SANITIZED session id (traversal/colon-safe, 128-char cap); ids that sanitize to nothing fall back to the legacy global file rather than crashing. Contexts merge over parents so nested scopes keep outer metadata. Rotation keeps exactly one backup. `enabled:false` short-circuits before any filesystem call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "withDebugLogContext safeDebugLogSessionId debugLogRelativePath rotateIfNeeded logAgentStreamError", limit: 10 });
```
(Direct tests: `tests/debug-log.test.ts:43` session-scoped file + metadata, :69 same-session appends across runs, :77 different sessions → different files, :85 unusable-id fallback to legacy global file, :96 sanitization table, :102 disabled writes nothing; `tests/stream-errors.test.ts:98` end-to-end `observer.stream_error` capture through a fake failing loop.)

## Verdict
Adopt ambient-context structured logging for any background worker pool: AsyncLocalStorage (or your runtime's equivalent), parent-merging contexts, sanitize-before-filename, swallow-all-errors writes, size-capped rotation, and an event-stream error hook that converts silent stopReason failures into named log lines. Adapt paths/event vocabulary. Omit nothing behavioral — the fail-open silence IS the design.
