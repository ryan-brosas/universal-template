<!-- capsule-v2 -->
# Client JSON route request — what is the minimal browser fetch contract for plugin routes, and where does schema trust begin?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should browser code call same-origin plugin endpoints so that error messages survive, bodies are only serialized when present, and the client never half-validates what the server already owns?

## One helper, one typed error
**Path/Symbol:** `src/client/OpenAICodexSettings.tsx:229-234 AccountRequestError`, `:236-251 jsonRequest`.
**Signature:** `class AccountRequestError extends Error { constructor(readonly code: string) }`; `async function jsonRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T>`.
**Data Shape:** success resolves to the parsed JSON body cast to `T` (may be `undefined`-shaped if the body failed to parse on an ok response); failure throws `AccountRequestError` whose `code` is either the server's `error` string field or `` `HTTP ${status}` ``.

### Decisive source
```ts
async function jsonRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: { accept: 'application/json', ...body === undefined ? {} : { 'content-type': 'application/json' } },
    credentials: 'same-origin',
    ...body === undefined ? {} : { body: JSON.stringify(body) },
  })
  const value: unknown = await response.json().catch(() => undefined)
  if (!response.ok) {
    const message = typeof value === 'object' && value !== null && 'error' in value
      && typeof value.error === 'string'
      ? value.error
      : `HTTP ${response.status}`
    throw new AccountRequestError(message)
  }
  return value as T
}
```

**Flow:** caller passes a route path plus optional payload → GETs omit both content-type and body entirely (so route handlers can distinguish "no patch" from "empty patch") → response body is parsed leniently (`catch(() => undefined)`) so a non-JSON error page still flows into the error branch → non-ok responses prefer the server's human-readable `error` field and fall back to the status code → callers match on `error.code` (e.g. `'remote-web-origin-not-trusted'`) for special states and show generic copy otherwise.
**Invariant:** credentials are always `same-origin` — the browser session cookie is the entire auth story, no tokens in JS; exactly one error type crosses every call site so `instanceof AccountRequestError` is reliable; the helper does NOT schema-validate success payloads — typing is a cast, and each consumer validates untrusted shapes at its own boundary (`usageFromStatus`, `readEnabled`) or trusts the plugin's own server contract; nothing leaks request bodies into thrown messages.
**Probe:** exercised indirectly by all three client spec suites, which stub global fetch with `Response` objects and drive every call site through it (settings catalog POST, quota status GET, fast-mode GET/POST). The settings spec asserts the exact POST body `{ models: ['gpt-5.6-sol'] }`; the fast-mode spec asserts `{ sessionId: 'session-a', enabled: true }`. Caveat recorded honestly: no spec imports `jsonRequest` directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.OpenAICodexSettings\\.jsonRequest$', limit: 10 });
```
Executed live against project `dsh-codex`: total 1, has_more false (`jsonRequest` Function 236-251, 6 inbound / 2 outbound edges).

## Verdict
Adopt the single-helper + typed-error pattern with conditional serialization headers and server-message-first error extraction. Adapt the credential mode, the error envelope key, and whether your stack needs timeout/abort wiring here (this repo delegates abort signals to individual call sites instead). Omit per-response schema validation inside the helper — keep untrusted-shape guards at the consumers that render the data. Coverage: `src/client/OpenAICodexSettings.tsx` is `no_recorded_issue` + `metadata_match`.
