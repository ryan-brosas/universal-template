<!-- capsule-v2 -->
# AppError sanitizing taxonomy — how do upstream axios errors become safe, branchable errors at the collaboration edge?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** Server-side collaboration code catches raw axios/DOM errors from many call sites — what one error class preserves enough structure to branch on (status 413, aborts) without leaking cookies/headers into logs?

## Constructor ladder
**Path/Symbol:** `apps/live/src/lib/errors.ts:AppError` (:20–79). Branch consumers: `database.ts` (`statusCode === 413`), `core.service.ts:updatePageProperties` (`appError.code === "ABORT_ERROR"`), `title-update-manager.ts`, every service catch.
**Signature:** `constructor(messageOrError: string | unknown, data?: Partial<Omit<AppError, "name" | "message">>)`.
**Data Shape:** Optional fields `statusCode?, method?, url?, code?, context?: Record<string, any>`; `name` always `"AppError"`.

### Decisive source
```ts
if (error instanceof AppError) { return error; }              // SAME instance back
if (typeof messageOrError === "string") { super(messageOrError); Object.assign(this, data ?? {}); return; }
if (error && typeof error === "object" && "isAxiosError" in error) {
  const responseData = axiosError.response?.data as any;
  super(responseData?.message || axiosError.message);
  this.statusCode = axiosError.response?.status;
  this.method = axiosError.config?.method?.toUpperCase();
  this.url = axiosError.config?.url;
  this.code = axiosError.code;                                 // config/headers/cookies dropped
  return;
}
if (error instanceof DOMException && error.name === "AbortError") { this.code = "ABORT_ERROR"; return; }
if (error instanceof Error) { super(error.message); this.code = error.name; return; }
super("Unknown error occurred");
```

**Flow:** five-arm classification at construction: (1) already-AppError ⇒ identity return (no re-wrap cost or context loss); (2) string message + optional data assign; (3) AxiosError ⇒ keep ONLY response status, uppercased method, url, axios code, and prefer the backend's `response.data.message` as the message — request config/headers/cookies are deliberately discarded ("prevents massive log bloat and sensitive data leaks"); (4) aborted fetch ⇒ DOMException AbortError normalized to `code: "ABORT_ERROR"` so callers can distinguish user-driven cancellation; (5) generic Error ⇒ its name becomes the code; anything else ⇒ fixed fallback.
**Invariant:** Downstream triage depends on exactly two preserved fields: `statusCode` (the 413 force-close decision in storeDocument) and `code === "ABORT_ERROR"` (silent debounce aborts vs real failures that re-arm retry timers). Wrapping an AppError must not produce a new object. The class is intentionally NOT typed per-cause — the discriminating info lives on two fields.
**Probe:** No dedicated upstream test. Deterministic pins: errors.ts contains the literal comment "no config, no headers, no cookies", `"isAxiosError" in error`, and `this.code = "ABORT_ERROR"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "AppError axios sanitize error status code", limit: 5 });
```
Observed at pin: rank-1 = `AppError` (errors.ts :20–79) with fan-in 21 across apps/live; remaining ranks are unrelated Django auth/csv helpers — scope by path when retrieving.

## Verdict
Adopt the five-arm constructor ladder, minimal-field axios projection, AbortError normalization, and identity passthrough for re-wraps; adapt which fields you preserve to your logging policy (Plane keeps method/url — drop them if URLs can carry secrets); omit nothing structural: consumers elsewhere in this leaf break if statusCode/code semantics drift. Coverage caveat: whole-file read @ pin; no upstream tests.
