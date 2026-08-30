<!-- capsule-v2 -->
# URL-elicitation error path (-32042) — how does a server signal "complete a browser prerequisite first" without trapping the client in an infinite retry loop?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** When should a server THROW `UrlElicitationRequiredError` instead of awaiting `elicitation/create`, and what two-loop-prevention mechanisms must ship with the throw?

## Request path vs error path, keyed one-shot prerequisite marker
**Path/Symbol:** `src/everything/tools/trigger-url-elicitation.ts` (whole file, 215L: schema w/ `errorPath` switch :19–36; module-level `issuedErrorPathElicitations` Set :66; stable-input key construction :126–131; error-path branch :146–172; request path :174–182). Registration gated on `clientCapabilities.elicitation?.url !== undefined` (:84–96) — URL mode is a SUB-capability of elicitation. Registered inside `registerConditionalTools`.

**Signature:** request path = `extra.sendRequest({ method: "elicitation/create", params: { mode: "url", url, message, elicitationId } }, ElicitResultSchema, { timeout: 10*60*1000 })`. Error path = `throw new UrlElicitationRequiredError([prerequisiteElicitation], message)` — MCP error code **-32042**, `data.elicitations[]` carries the prerequisite URL-mode params.

**Data Shape:** `const issuedErrorPathElicitations = new Set<string>()` — keys are `` `${sessionId}\u0000${url}\u0000${requestedElicitationId ?? ""}` `` built from the inputs a real client RESENDS VERBATIM when retrying the original tool call (the server-generated prerequisite id is deliberately NOT part of the key).

### Decisive source
```ts
// trigger-url-elicitation.ts:146-172 — two loop guards on every -32042 throw
if (errorPath) {
  if (issuedErrorPathElicitations.has(errorPathKey)) {
    // Retry of a satisfied prerequisite: clear the one-shot marker and
    // ignore errorPath, falling through to the request path below.
    issuedErrorPathElicitations.delete(errorPathKey);
  } else {
    issuedErrorPathElicitations.add(errorPathKey);
    const prerequisiteElicitation: ElicitRequestURLParams = {
      mode: "url",
      url: "https://modelcontextprotocol.io",  // DIFFERENT from the failing URL
      message: "Open this link to satisfy the prerequisite, then retry the request.",
      elicitationId: randomUUID(),
    };
    throw new UrlElicitationRequiredError([prerequisiteElicitation],
      "This request requires browser-based authorization.");
  }
}
```

**Flow:** client retries the SAME args after satisfying an out-of-band prerequisite → key matches ⇒ marker deleted, `errorPath` ignored, request path executes → otherwise originating call ⇒ marker added, `-32042` thrown with a prerequisite pointing at a DIFFERENT URL → client handles the prerequisite, retries → loop broken by both guards.

**Invariants (each prevents its own infinite loop):**
1. **Prerequisite URL ≠ failing URL** — reusing the original URL makes the client complete it, retry, and hit the same -32042 forever (test asserts this explicitly).
2. **One-shot marker keyed on STABLE inputs only** — keying on the resolved/random elicitationId would change every call and never match, re-throwing forever. A real client retries with identical args and does NOT echo the server-generated prerequisite id.
3. On recognized retry, `errorPath` is IGNORED (fall through to request path) — honoring it would re-enter the throw.
4. Known demo debt (recorded in source :55–65): entries are only removed on a recognized retry; production hosts should use TTL eviction.

**Probe:** `src/everything/__tests__/tools.test.ts:926–1024` — asserts `error.code === -32042`, `prerequisite.mode === 'url'`, `prerequisite.url === 'https://modelcontextprotocol.io'` AND `!== 'https://example.com/connect'`, string-typed prerequisite `elicitationId`; then the retry case drives the same args twice proving the second call takes the request path (`mockSendRequest` called) instead of re-throwing. Additional registration-gate pins at :721–832 (`elicitation: { url: {} }` present/absent/undefined).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "UrlElicitationRequiredError -32042 prerequisite elicitation error path", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the error path for prerequisites that must complete BEFORE a request can proceed (auth flows), the different-URL rule, and the stable-keyed one-shot marker; adapt the marker store to a TTL'd map for long-lived sessions; omit nothing from the loop guards — both are load-bearing. Extends `elicitation.md` (form-vs-URL contract) with the server-side state machine the spec page does not cover.
