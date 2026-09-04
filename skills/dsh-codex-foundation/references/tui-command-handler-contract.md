<!-- capsule-v2 -->
# Codex command handler — what belongs in a UI-neutral chat-command executor: argv grammar, arity guards, redaction-bounded failures, and preference projections?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** a provider's `/command` runs in many hosts — how should one handler parse input, guard arity, project service state into text, and keep errors secret-free?

## /codex handler plane
**Path/Symbol:** `src/tui.ts:288-326 handler`, guards/formatters `:91-104 success/failure/safeMessage`, `:221-253 formatExpiry/formatUsage/formatConfig`, `:255-272 updateSetting`.
**Signature:** `handler({ rawInput }): Promise<CommandResult>` where `CommandResult = { kind:'success'|'error', text }`; `updateSetting(service, key, enabled)`; `formatUsage(usage: OpenAICodexUsage): string`; `safeMessage(error: unknown): string`.
**Data Shape:** actions `status|login|logout|usage|config|set`; `set <key> <on|off>` with keys `read-image|imagegen-other-models|websocket-context|native-compaction`.

### Decisive source
```ts
async handler({ rawInput }) {
  const parts = rawInput.trim().split(/\s+/u).filter(Boolean)
  const action = parts[0] ?? 'status'
  try {
    switch (action) {
      case 'status': { /* login-state first, then stored auth + expiry line */ }
      case 'set': {
        if (parts.length !== 3 || (parts[2] !== 'on' && parts[2] !== 'off')) return failure(HELP)
        await updateSetting(service, parts[1] as string, parts[2] === 'on')
        return success(formatConfig(service))
      }
      default:
        return failure(HELP)
    }
  } catch (error: unknown) {
    return failure(safeMessage(error))
  }
}

function safeMessage(error: unknown): string {
  return (error instanceof Error ? error.message : String(error))
    .replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/gu, '[redacted token]')
    .replace(/(\b(?:code|token|refresh_token|access_token)=)[^&\s]+/giu, '$1[redacted]')
    .slice(0, 1000)
}
```

**Flow:** whitespace-tokenized argv with empty input defaulting to `'status'` → per-action strict arity (`login/logout/usage/config` require exactly 1 part; `set` exactly 3 with literal `on|off`) → violations and unknown actions return the multi-line HELP text as a *failure* result rather than throwing → successful mutations echo the fresh `formatConfig(service)` projection so the user sees post-write state, never the requested state → every thrown error is funneled through `safeMessage` into an error CommandResult.
**Invariant:** handler output is always a structured result — exceptions never escape to the host shell; `status` reads the controller's live LoginState BEFORE the store (a signing-in or errored background login outranks stored credentials); expiry rendering tolerates undefined AND NaN dates by omitting the clause entirely; usage projection prefers `limit.name ?? limit.id`, renders each window as `(Ns): X.X% remaining`, appends individual-limit and credits lines only when present (`unlimited ? 'unlimited' : balance ?? 'available'`), and degrades to "usage is currently unavailable" on an empty projection; the tui `safeMessage` twin of bin.ts's redactor adds `.slice(0, 1000)` because its output lands in a persisted chat result rather than transient stderr; unknown setting keys throw with `JSON.stringify(key)` so the message quotes the exact bad token.
**Probe:** `tests/tui.spec.ts:96-112` pins byte-exact outputs: `' status'` (leading space tolerated) → `'OpenAI Codex is signed in. Access token expires 2026-08-17T00:00:00.000Z; refresh is automatic.'`; `' usage'` → `'Codex (18000s): 62.5% remaining'`; `' config'` contains `'read-image: on'`; `' set native-compaction on'` calls `updateResponsePreferences({ useNativeCompaction: true })` and echoes `'native-compaction: on'`. Executed green this pass. Caveat: failure/arity paths are not directly asserted in this spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.tui\\.(handler|formatUsage|formatConfig|formatExpiry|updateSetting)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 5, has_more false.

## Verdict
Adopt total argv grammar with HELP-as-failure, echo-after-write projections, NaN-tolerant date rendering, and redaction-plus-truncation for any error text that persists in a transcript. Adapt action names, setting vocabulary, and the redactor's value patterns to your credential shapes. Omit trusting upstream error messages or echoing pre-write preference values. Coverage: src/tui.ts, tests/tui.spec.ts `no_recorded_issue` + `metadata_match`.
