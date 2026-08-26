<!-- capsule-v2 -->
# Typed error round-trip — which errors survive the wire as classes, and how are stacks rebuilt?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When the server rejects with an error, how does the client get a typed error with useful stack and call log — and where is the client/server asymmetry that breaks naive ports?

## Client parseError rebuilds by name; server twin deliberately plain
**Path/Symbol:** `packages/playwright-core/src/client/errors.ts:parseError` (58-75) + class hierarchy (22-50) + dispatch site `client/connection.ts:246-255`.
**Signature:** `parseError(error: SerializedError): PlaywrightError`; `serializeError(e: any): SerializedError` (52-56); SerializedError `{ error?: { message, stack, name }, value?, errorDetails? }`.
**Data Shape:** wire carries `{ error: { message, stack, name }, errorDetails }` + `log: string[]` (call log lines); client classes: `PlaywrightError { log: string[], details? }` ← `TimeoutError`, `TargetClosedError`, `AbortError`.

### Decisive source
```ts
export function parseError(error: SerializedError): PlaywrightError {
  if (!error.error) {
    if (error.value === undefined)
      throw new Error('Serialized error must have either an error or a value');
    return parseSerializedValue(error.value, undefined);
  }
  let e: PlaywrightError;
  if (error.error.name === 'TimeoutError')
    e = new TimeoutError(error.error.message);
  else if (error.error.name === 'TargetClosedError')
    e = new TargetClosedError(error.error.message);
  else if (error.error.name === 'AbortError')
    e = new AbortError(error.error.message);
  else
    e = Object.assign(new PlaywrightError(error.error.message), { name: error.error.name });
  e.stack = error.error.stack || '';
  return e;
}
```

**Flow:** dispatch receives rejection → `parseError` reconstructs the CLASS by serialized name so `instanceof TimeoutError` / `instanceof TargetClosedError` work on the client (`isTargetClosedError` drives close-handling policy everywhere). Then dispatch decorates: attaches `signal.reason` as cause for aborted calls, sets `.log` from the reply, appends `formatCallLog(log)` ("Call log:" block) to the message, and runs the per-method ErrorDetails validator to populate `.details`. The SERVER's own twin (`server/errors.ts:parseError`, 57-67) intentionally produces PLAIN `new Error(...)` — it exists for evaluating user JS in-page and must not leak Playwright classes into page contexts. `serializeError` mirrors the split: real Errors serialize `{error:{message,stack,name}}`; non-Errors serialize as values.
**Invariant:** Name-based reconstruction must cover every class your client checks with instanceof; unknown names still yield PlaywrightError with the original name preserved; stack is server-side (the library frames the USER sees are re-captured client-side in `_wrapApiCall`, not taken from this stack).
**Probe:** `grep -c "error.error.name === 'TimeoutError'" packages/playwright-core/src/client/errors.ts` → `1`; `grep -c "Object.assign(new PlaywrightError" packages/playwright-core/src/client/errors.ts` → `1`; `grep -n "e.name = error.error.name" packages/playwright-core/src/server/errors.ts` → line 65 (server twin: plain Error + assigned name, no classes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "serializeError PlaywrightError client errors", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph caveat: BM25 ranks the server twin first for bare "parseError"; scope queries with "client errors" and check the returned file span before citing.)

## Verdict
Adopt name-keyed typed reconstruction, cause/log/details decoration at the dispatch layer, and the deliberate client/server asymmetry. Adapt the class set to your domain's error taxonomy (keep unknown-name fallback generic). Omit `serializeError`'s value-path unless you round-trip thrown non-Errors. Direct behavior pinned by crash/close tests asserting messages and classes (`tests/library/page-event-crash.spec.ts` line 51+ asserts 'crashed'/closed errors; timeout tests assert `Timeout Nms exceeded` via multiclient.spec.ts line 110).
