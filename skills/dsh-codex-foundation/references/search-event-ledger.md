<!-- capsule-v2 -->
# Search event ledger — how does a plugin register a durable session event in a host vocabulary it does not own, and record the request before dispatch?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how can provider telemetry become a first-class durable session event without mutating host core or leaking credentials into the log?

## Plugin-owned session event vocabulary extension
**Path/Symbol:** `src/search-event.ts:9 OPENAI_CODEX_SEARCH_MODEL_REQUEST_EVENT`, `src/search-event.ts:11-16 SessionEventMap augmentation`, `src/search-event.ts:25-30 installOpenAICodexSearchEvent`, `src/search-event.ts:38-46 recordOpenAICodexSearchRequest`.
**Signature:** `installOpenAICodexSearchEvent(): void`; `recordOpenAICodexSearchRequest(ctx: Context, request: OpenAICodexSearchRequestRecord): void`.
**Data Shape:** one constant event name `'web/openai-codex-search-llm-request'` typed into the host's `SessionEventMap` as the exact secret-free `OpenAICodexSearchRequestRecord` (`{ endpoint, body }` — no credential fields); the record is appended to the initiating agent's session only.

### Decisive source
```ts
export function installOpenAICodexSearchEvent(): void {
  if (!(KNOWN_SESSION_EVENT_TYPES instanceof Set)) {
    throw new Error('dsh-openai-codex: this Harness build does not expose an extensible session event vocabulary')
  }
  KNOWN_SESSION_EVENT_TYPES.add(OPENAI_CODEX_SEARCH_MODEL_REQUEST_EVENT)
}

export function recordOpenAICodexSearchRequest(ctx: Context, request: OpenAICodexSearchRequestRecord): void {
  ctx.get('agents')?.currentInitiator()?.session.append(
    OPENAI_CODEX_SEARCH_MODEL_REQUEST_EVENT,
    request,
  )
}
```

**Flow:** plugin init registers the event name once for the process lifetime → search provider resolves defaults into the exact request → `recordOpenAICodexSearchRequest` appends it to the initiating agent's session STRICTLY BEFORE the network dispatch → fetch happens. Searches outside an agent turn have no owning session and produce no log (optional-chain swallow).
**Invariant:** the public build exports its known-event collection as read-only because core must not mutate it accidentally — the runtime value is deliberately still a `Set`, consulted on every persistence read, so adding one entry is safe but structural doubt hard-fails with an explicit error; registration survives dispose/HMR so sessions written before a reload stay readable; records exclude credentials by type; the generic host event `web/search-model-request` is never registered by this plugin.
**Probe:** `tests/search.spec.ts:235-265` (after a real search through the mounted runtime: `KNOWN_SESSION_EVENT_TYPES.has(...)` true; generic event absent; `append` called exactly once with the full secret-free body; `append.mock.invocationCallOrder[0] < fetch.mock.invocationCallOrder[0]`; still registered after `fiber.dispose()`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.search-event\\.(installOpenAICodexSearchEvent|recordOpenAICodexSearchRequest)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 2, has_more false.

## Verdict
Adopt the guard-railed vocabulary registration (instanceof check + explicit failure) and record-before-dispatch ordering keyed to the current agent initiator. Adapt the event name, record shape, and host lookup path; keep the credential-exclusion boundary in the record type itself. Omit mutating host collections that are not runtime Sets or logging when no owning session exists. Coverage: `src/search-event.ts` is `no_recorded_issue` + `metadata_match`; behavior is pinned inside `tests/search.spec.ts` rather than by a dedicated spec file.
