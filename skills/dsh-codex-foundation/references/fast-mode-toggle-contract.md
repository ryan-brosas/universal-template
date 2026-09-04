<!-- capsule-v2 -->
# Fast Mode session toggle — how should a per-session control write through a route while never lying about state?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how does a composer button load the current session's flag, POST an optimistic flip, and recover — with aborts owned across GET, POST, and unmount races?

## Server-authoritative toggle with identity-checked abort ownership
**Path/Symbol:** `src/client/OpenAICodexFastModeToggle.tsx:28-31 readEnabled`, `:33-39 isEligible`, `:45-47 requestUrl`, `:65-67 controllerRef`, `:72-108 load effect`, `:121-152 toggle`, `src/fast-mode-paths.ts OPENAI_CODEX_FAST_MODE_PATH`.
**Signature:** `function readEnabled(value: unknown): boolean | undefined`; `function isEligible(state: ModelDirectoryState): boolean`; `function requestUrl(sessionId: string): string` → `` `${OPENAI_CODEX_FAST_MODE_PATH}?sessionId=${encodeURIComponent(sessionId)}` ``; `toggle(): void`.
**Data Shape:** wire contract is two shapes on one path — `GET …?sessionId=… → { enabled: boolean }` and `POST { sessionId, enabled } → { enabled: boolean }`; anything else (non-boolean field, non-ok status, transport throw) is `undefined` and treated as failure.

### Decisive source
```ts
const toggle = (): void => {
  if (state.status !== 'ready' || busy) return
  controllerRef.current?.abort()
  const controller = new AbortController()      // new owner for this flight
  controllerRef.current = controller
  const next = !state.enabled
  setState(current => ({ ...current, status: 'loading' }))   // optimistic ONLY in busy-ness
  void (async () => {
    try {
      const response = await fetch(OPENAI_CODEX_FAST_MODE_PATH, {
        method: 'POST', credentials: 'same-origin',
        headers: { accept: 'application/json', 'content-type': 'application/json' },
        body: JSON.stringify({ sessionId, enabled: next }),
        signal: controller.signal,
      })
      const enabled = response.ok ? readEnabled(await response.json().catch(() => undefined)) : undefined
      if (!controller.signal.aborted) {
        setState(enabled === undefined
          ? { status: 'error', enabled: state.enabled }   // restore PRIOR truth on failure
          : { status: 'ready', enabled })                 // server response is authoritative
      }
    } catch {
      if (!controller.signal.aborted) setState({ status: 'error', enabled: state.enabled })
    } finally {
      if (controllerRef.current === controller) controllerRef.current = undefined  // identity check
    }
  })()
}
```

**Flow:** directory snapshot gates eligibility exactly like the quota chip but case-SENSITIVELY (`model.startsWith('gpt-')`, no lowercase — a real divergence from QuotaIndicator's `isGptModel`) → eligible sessions GET their per-session state once; ineligible ones render null before any fetch → click flips only when ready, aborting any in-flight request first → POST result replaces state; failures restore the prior `enabled` under `'error'` → tooltip/aria copy is state-specific (`fastModeLoadingTitle` / `UnavailableTitle` / `EnabledTitle` / `DisabledTitle`) and bilingual-exact.
**Invariant:** the displayed enabled value is always either the server's last confirmed value or its restored predecessor — never the optimistic guess; stale flights can never clear or overwrite a newer one because cleanup and completion both check `controllerRef.current === controller`; eligibility re-evaluation aborts the old fetch and resets to loading; unmount aborts whatever is in flight (GET or POST); the button is `disabled` + `aria-busy` while not ready and carries `aria-pressed` for state.
**Probe:** `tests/openai-codex-fast-mode.client.spec.tsx`: 6 cases pin exact bilingual titles, the GET query-param shape and POST body `{ sessionId: 'session-a', enabled: true }` against the imported `OPENAI_CODEX_FAST_MODE_PATH`, aria/title semantics plus bolt fill/outline states, hide-without-fetch for non-GPT/wrong-provider directories, disabled-during-load with unmount abort of the pending GET, prior `aria-pressed='true'` preserved after a 500 POST, and unmount abort of an in-flight POST.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.OpenAICodexFastModeToggle\\.(readEnabled|isEligible|requestUrl|toggle)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false (`isEligible` 33-39, `readEnabled` 28-31, `requestUrl` 45-47, `toggle` 121-152). Graph note: `toggle` reports 0 inbound callers (pure event handler) while `trace_path('refresh')` merges module-local closures across files — both resolved by direct source reads.

## Verdict
Adopt server-authoritative toggles with prior-state restore, identity-checked single-controller ownership, and pre-network eligibility gating. Adapt the eligibility predicate (and reconcile case sensitivity deliberately — this repo's two composer surfaces differ), the wire shapes, and the copy keys. Omit local persistence of the flag: the provider-side registry (`fast-mode-registry` capsule) owns it; the client merely projects. Coverage: source and spec are `no_recorded_issue` + `metadata_match`.
