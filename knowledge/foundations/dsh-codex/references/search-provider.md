<!-- capsule-v2 -->
# Standalone web-search provider — fixed-endpoint OAuth search with secret-free request records

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how to expose a ChatGPT-Codex standalone web-search endpoint as a dsh `WebSearchProvider` so the request is recorded secret-free before dispatch, cancellation is honored before any credential read, the account id is derived from the JWT, and the forward-compatible result DTO is normalized into citeable, deduplicated sources?

## OpenAICodexSearchProvider
**Path/Symbol:** `src/search.ts:OpenAICodexSearchProvider` (class), `src/search.ts:mapOpenAICodexSearchResponse`, `src/search.ts:accountIdFromToken`, `src/search.ts:externalWebAccess`, `src/search.ts:providerMessage`, `src/search.ts:abortable`, `src/search.ts:throwIfSearchAborted`, `src/search.ts:citeableUrl`.
**Signature:** `class OpenAICodexSearchProvider implements WebSearchProvider { id = OPENAI_CODEX_SEARCH_PROVIDER; constructor(options: OpenAICodexSearchProviderOptions); available(): boolean; search(request: WebSearchRequest, signal?: AbortSignal): Promise<WebSearchResult> }`.
**Data Shape:** `SearchRequestBody` = `{ id, model, input: [{type:'message',role:'user',content:[{type:'input_text',text}]}], commands:{search_query:[{q}]}, settings:{search_context_size, allowed_callers:['direct'], external_web_access: boolean|'indexed'}, max_output_tokens }`. `OpenAICodexSearchRequestRecord` = `{ endpoint, body }` (secret-free). Result DTO items are forward-compatible: only `type === 'text_result'` items with a citeable `http(s)` `url` are kept, deduplicated by URL, with optional `title`/`snippet`.

### Decisive source
```ts
// src/search.ts — account id derived from the OAuth JWT, never stored separately
function accountIdFromToken(access: string): string {
  const parts = access.split('.')
  if (parts.length !== 3 || parts[1] === undefined) throw new Error('invalid JWT')
  const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8')) as Record<string, unknown>
  const auth = payload['https://api.openai.com/auth']
  if (typeof auth !== 'object' || auth === null || Array.isArray(auth)) throw new Error('missing auth claim')
  const accountId = (auth as Record<string, unknown>)['chatgpt_account_id']
   if (typeof accountId !== 'string' || accountId.length === 0) throw new Error('missing account id')
  return accountId
}

// Forward-compatible DTO normalization: unknown types/fields ignored, citeable URLs deduped
export function mapOpenAICodexSearchResponse(value: unknown): WebSearchResult {
  if (!isRecord(value) || typeof value['output'] !== 'string') {
    throw new WebError('OpenAI Codex returned a search response without string output', 'WEB_PROVIDER_ERROR')
  }
  const output = value['output']
  const rawResults = value['results']
  if (rawResults !== undefined && !Array.isArray(rawResults)) {
    throw new WebError('OpenAI Codex returned a search response with non-array results', 'WEB_PROVIDER_ERROR')
  }
  const sources: WebSearchSource[] = []
  const seen = new Set<string>()
  for (const item of rawResults ?? []) {
    if (!isRecord(item) || item['type'] !== 'text_result') continue
    const url = citeableUrl(item['url'])   // http/https only, else undefined
    if (url === undefined || seen.has(url)) continue
    seen.add(url)
    const title = optionalString(item, 'title')
    const snippet = optionalString(item, 'snippet')
    sources.push({ url, ...title === undefined ? {} : { title }, ...snippet === undefined ? {} : { snippet } })
  }
  return { ...output.length === 0 ? {} : { content: output }, sources, truncated: false }
}

// Abortable auth refresh: race auth against caller cancellation, stable WEB_ABORTED
function abortable<T>(operation: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (signal === undefined) return operation
  if (signal.aborted) return Promise.reject(searchAborted(signal))
  return new Promise<T>((resolve, reject) => {
    const onAbort = (): void => { reject(searchAborted(signal)) }
    signal.addEventListener('abort', onAbort, { once: true })
    void operation.then(
      (value) => { signal.removeEventListener('abort', onAbort); resolve(value) },
      (error) => { signal.removeEventListener('abort', onAbort); reject(error) },
    )
  })
}

// Redact JWT-like tokens from provider diagnostics, bound length
function providerMessage(value: unknown): string | undefined {
  // raw = error string | error.message | message
  return raw?.replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/gu, '[REDACTED]').slice(0, 1000)
}
```

**Flow:** `search` first `throwIfSearchAborted`, then resolves auth via `abortable(models.getAuth(OPENAI_CODEX_PROVIDER), signal)`; missing/empty `access` → `WEB_PROVIDER_CREDENTIAL_MISSING` with a "run login again" hint; `accountIdFromToken` derives the account id; the body is built and `recordRequest?.({endpoint, body})` fires BEFORE `fetch` (test asserts invocation order); `fetch` uses `redirect:'error'`, `authorization: Bearer <access>`, `chatgpt-account-id`, `originator:'deepseek-harness'`, and forwards the `signal`. Non-OK maps 401/403 → `WEB_PROVIDER_CREDENTIAL_MISSING` (+ re-login hint) and other statuses → `WEB_PROVIDER_ERROR`; unparseable JSON → `WEB_PROVIDER_ERROR`; then `mapOpenAICodexSearchResponse` normalizes the payload.
**Invariant:** the request is recorded secret-free before any network dispatch; cancellation is honored before credential read and throughout (stable `WEB_ABORTED` code); only citeable `http(s)` URLs survive and duplicates collapse; unknown DTO types/fields are ignored for forward compatibility; malformed envelope fields fail at the network boundary; provider diagnostics redact JWT material and stay bounded; the account id is derived from the JWT payload, not stored separately.
**Probe:** `tests/search.spec.ts` — "retains generated output and deduplicated citeable structured sources" (drops `javascript:` URL, unknown DTO type, duplicate URL), "accepts an empty answer and absent results", "rejects malformed response envelope fields", "maps cached/indexed/live mode, authenticates, and records before dispatch" (asserts exact body, headers, endpoint, and `recordRequest` invocation order < `fetch`), "forwards cancellation and rejects a pre-aborted request before reading credentials" (spy on `store.read` not called), "requires a signed-in credential", and "maps authorization, malformed JSON, malformed success, and transport failures".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", query: "OpenAICodexSearchProvider standalone search recordRequest accountIdFromToken externalWebAccess", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the standalone web-search provider: fixed first-party endpoint with `redirect:'error'`, account id derived from the OAuth JWT, secret-free `recordRequest` fired before dispatch, abortable auth refresh racing caller cancellation with a stable `WEB_ABORTED` code, forward-compatible result-DTO normalization (citeable `http(s)` URLs only, deduped, unknown types ignored), and JWT-redacting bounded provider diagnostics. Adapt the endpoint, the `originator` header value, and the search-mode → `external_web_access` mapping (`cached`→`false`, `indexed`→`'indexed'`, `live`→`true`) to the target provider. Omit the `OPENAI_CODEX_SEARCH_PROVIDER` id and the `@earendil-works/pi-ai` `createModels`/auth plumbing when porting to another provider. Coverage: `src/search.ts` and `tests/search.spec.ts` both `no_recorded_issue` + `metadata_match`; the vitest runner is not installed in this read-only checkout, so deterministic probes were executed against the actual source (Node strip-types, external imports stubbed) and matched every test assertion (mapping, dedup, envelope rejection, mode mapping, auth headers, record-before-dispatch ordering, pre-abort credential-read skip, error mapping).
