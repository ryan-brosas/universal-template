<!-- capsule-v2 -->
# ws-error-mapping-fork-nudge — How do server method exceptions map onto wire error objects, and which error shapes carry side-channel directives?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What exactly travels back to the browser when a registered method throws — and where does the shouldFork signal come from?

## Method-error → CommResponseError mapping
**Path/Symbol:** `app/server/lib/Client.ts:_onMessageImpl` (:489–540); unknown-method branch :504–507; catch-and-map :511–537.
**Signature:** every request gets EXACTLY one response `{reqId, data?}` or `{reqId, error, errorCode?, details?, status?, shouldFork?}`; unknown method ⇒ `{reqId, error: "Unknown method X"}`.
**Data Shape:** ErrorWithCode fields read off the thrown error: `message` (always sent), `code`→errorCode, `details`, `status`; special-cases below.

### Decisive source
```ts
const skipStack = (
  !err.stack ||
  err.stack.match(/^SandboxError:/) ||
  (typeof code === "string" && code.startsWith("AUTH_NO"))
);
this._log.warn(null, "Responding to method %s with error: %s %s",
  request.method, skipStack ? err : err.stack, code || "");
response = { reqId: request.reqId, error: err.message };
if (err.code)    { response.errorCode = err.code; }
if (err.details) { response.details = err.details; }
if (err.status)  { response.status = err.status; }
if (typeof code === "string" && code === "AUTH_NO_EDIT" && err.accessMode === "fork") {
  response.shouldFork = true;
}
```

**Flow:** request arrives (heartbeats short-circuit earlier: `request.beat` ⇒ log rawInfo incl. client-supplied docId "caution: trusting client for docId" and NO reply) → unknown method ⇒ plain error string → method throws ⇒ map message/code/details/status onto the wire object → ALWAYS finish via `sendMessageOrInterrupt(response)` so even failures get an answer. Log-side noise discipline: SandboxError stacks and AUTH_NO* stacks are suppressed as useless (:513–515 comment).
**Invariant:** reqId echo is unconditional — the client correlates every response, including errors; error MESSAGES are client-safe but stacks never travel; `shouldFork:true` rides ONLY the exact conjunction AUTH_NO_EDIT + accessMode==="fork" (a document in fork mode edited without permission ⇒ UI nudges user to save their own copy). Porters who broaden shouldFork to all auth errors break the fork-mode UX contract.
**Probe:** `test/server/Comm.ts:228` ("should return error when a call fails"), :243 ("should return error for unknown methods") — error shape and reqId echo pinned.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_onMessageImpl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exhaustive one-response-per-request rule + field-by-field error mapping + exact shouldFork conjunction. Adapt error vocabulary; omit sandbox-specific stack filtering if you have no sandbox boundary.
