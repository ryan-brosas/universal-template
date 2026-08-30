<!-- capsule-v2 -->
# Registry Error Taxonomy — how do I map HTTP failures to typed, actionable errors without losing the server's own message?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** When a registry fetch fails, what error object should a porter construct so callers can branch on code/status while users still see the server's explanation and a next step?

## Typed status→subclass ladder over one enriched base
**Path/Symbol:** `packages/shadcn/src/registry/errors.ts:33-77` (`RegistryError`), `:79-191` (status subclasses), `packages/shadcn/src/registry/fetcher.ts:62-111` (status mapping + body extraction).
**Signature:** `new RegistryError(message, { code?, statusCode?, cause?, context?, suggestion? })`; subclasses take `(url, cause?)` where `cause` is often the *server's message string*, not an Error.
**Data Shape:** Every error carries `code` (const-object union `RegistryErrorCode`: NETWORK_ERROR, NOT_FOUND, GONE, UNAUTHORIZED, FORBIDDEN, FETCH_ERROR, NOT_CONFIGURED, INVALID_CONFIG, MISSING_ENV_VARS, LOCAL_FILE_ERROR, PARSE_ERROR, VALIDATION_ERROR, UNKNOWN_ERROR), optional `statusCode`, `context` record, `suggestion`, `timestamp`, and `toJSON()` for structured logging. Subclasses set `this.name` AFTER `super()` because the base hardcodes `name = "RegistryError"`.

### Decisive source
```ts
// fetcher.ts — extract server detail BEFORE choosing the class
if (!response.ok) {
  let messageFromServer = undefined
  if (response.headers.get("content-type")?.includes("application/json")) {
    const json = await response.json()
    const parsed = z.object({
      detail: z.string().optional(),   // RFC 7807
      title: z.string().optional(),
      message: z.string().optional(),
      error: z.string().optional(),
    }).safeParse(json)
    if (parsed.success) {
      messageFromServer = parsed.data.detail || parsed.data.message
      if (parsed.data.error) {
        messageFromServer = `[${parsed.data.error}] ${messageFromServer}`
      }
    }
  }
  if (response.status === 401) throw new RegistryUnauthorizedError(url, messageFromServer)
  if (response.status === 404) throw new RegistryNotFoundError(url, messageFromServer)
  if (response.status === 410) throw new RegistryGoneError(url, messageFromServer)
  if (response.status === 403) throw new RegistryForbiddenError(url, messageFromServer)
  throw new RegistryFetchError(url, response.status, messageFromServer)
}
```

**Flow:** non-OK response → content-type-gated JSON probe → safeParse four-field shape → pick server detail (RFC 7807 `detail` preferred over `message`; `error` prefixed as `[tag] detail`) → exact-match 401/404/410/403 to their typed subclass → everything else becomes `RegistryFetchError(url, statusCode, responseBody)` whose suggestion itself varies by status band (404 / 500 / other-4xx / default network hint).
**Invariant:** The server's own explanation must survive into the thrown error (as `cause` string and inside `message`); never replace it with a generic phrase. Config-shape errors reuse the same base (`ConfigMissingError`, `ConfigParseError` with ZodError path formatting `- a.b.c: msg`) so ONE catch site handles the whole CLI.
**Probe:** `packages/shadcn/src/registry/fetcher.test.ts:148-170` — MSW returns bare 404/401/403/410 responses; each asserts `rejects.toThrow(RegistryNotFoundError|RegistryUnauthorizedError|RegistryForbiddenError|RegistryGoneError)` respectively. Runner note: vitest configured but node_modules absent in this read-only checkout — behavior pinned by direct test read, not executed here.
**Coverage:** errors.ts + fetcher.test.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "RegistryError code context toJSON not found unauthorized", limit: 10 });
```
Executed live: top hit `registry.errors.RegistryError.toJSON` (errors.ts:65-76), with
`RegistryNotFoundError` also in the top 10. (The looser phrase "registry error
statusCode suggestion" MISSES — it ranks handle-error/logger utilities first;
use class vocabulary.)

## Verdict
Adopt the taxonomy skeleton (code enum + context + suggestion + toJSON) and the RFC 7807-first body extraction ladder verbatim. Adapt subclass naming/messages to your domain vocabulary; adapt zod to your validator. Omit shadcn-specific suggestion copy that references `components.json`/`npx shadcn init`.
