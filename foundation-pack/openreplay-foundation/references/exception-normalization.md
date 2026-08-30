<!-- capsule-v2 -->
# Exception capture ladder — how are Error objects, string throws, and promise rejections normalized into one message?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What normalization must a porter apply so all three failure shapes carry name/message/stack?

## error→stack-parse; non-error→split-on-colon; rejection→stringify
**Path/Symbol:** `tracker/tracker/src/main/modules/exception.ts` — `getExceptionMessage` (:30–40), `getExceptionMessageFromEvent` (:42–77: colon split :51–55, `'Unhandled Promise Rejection'` :73), patcher (:79–104), stack source `error-stack-parser-es`.
**Signature:** `getExceptionMessage(error, fallbackStack, metadata?): Message`; `getExceptionMessageFromEvent(e, context?, metadata?): Message | null`.
**Data Shape:** output `JSException(name, message, JSON.stringify(StackFrame[]), JSON.stringify(metadata))`; default frame from ErrorEvent `{colno,lineno,filename}`.

### Decisive source
```ts
if (e.error instanceof Error) {
  return getExceptionMessage(e.error, getDefaultStack(e), metadata)
} else {
  let [name, message] = e.message.split(':')
  if (!message) { name = 'Error'; message = e.message }
  ...
} else if (... instanceof context.PromiseRejectionEvent) {
  ...
  return JSException('Unhandled Promise Rejection', message, '[]', ...)
```

**Flow:** window `error` + `unhandledrejection` listeners per context → Error instances get real stacks via parser → thrown strings split on the FIRST colon into name/message (no colon ⇒ generic `Error`) → rejected non-Errors stringify (fallback String()) → attachContextCallback patches every iframe identically.
**Invariant:** The colon split uses the first `:` only — a porter using `split(':')` destructuring must guard the missing-message case exactly as upstream (`if (!message)`). Stack parse failures fall back to the event-derived single frame, never throw.
**Probe:** `grep -c "e.message.split" tracker/tracker/src/main/modules/exception.ts` → `1`; `grep -c 'Unhandled Promise Rejection' tracker/tracker/src/main/modules/exception.ts` → `1`; `grep -c 'captureExceptions: true' tracker/tracker/src/main/modules/exception.ts` → `1`; direct tests `tests/exception.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "getExceptionMessage JSException PromiseRejectionEvent", limit: 10 });
```

## Verdict
Adopt three-shape normalization. Adapt metadata envelope. Omit per-iframe patching for single-context targets.
