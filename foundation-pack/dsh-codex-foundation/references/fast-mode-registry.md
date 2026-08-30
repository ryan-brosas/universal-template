<!-- capsule-v2 -->
# Fast Mode — bounded per-session boolean state with LRU eviction and priority payload decoration

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how to keep a bounded, process-local per-session on/off flag that never leaks credentials, evicts the least-recently-used session, and injects a wire hint (`service_tier: 'priority'`) only for the owning provider's requests?

## FastModeRegistry + withOpenAICodexFastMode
**Path/Symbol:** `src/fast-mode.ts:FastModeRegistry` (25-89), `src/fast-mode.ts:isFastModeSessionId` (14-18), `src/adapter.ts:withOpenAICodexFastMode` (85-110).
**Signature:** `new FastModeRegistry(maxSessions = 256)`; `isEnabled(sessionId: unknown): boolean`; `set(sessionId: unknown, enabled: boolean): void`; `withOpenAICodexFastMode(provider: Provider, fastMode: FastModeRegistry | undefined): Provider`.
**Data Shape:** `enabledSessions: Map<string, true>` — positive-only (disabling deletes the key). Session ids are opaque strings, trimmed non-empty, ≤256 UTF-16 units. Capacity bounded 1..256. The wrapper clones the provider and overrides `streamSimple`, decorating only the `onPayload` result when the session is enabled for the owning provider.

### Decisive source
```ts
// src/fast-mode.ts
export function isFastModeSessionId(value: unknown): value is string {
  return typeof value === 'string'
    && value.trim().length > 0
    && value.length <= OPENAI_CODEX_FAST_MODE_MAX_SESSION_ID_LENGTH
}
export class FastModeRegistry {
  private readonly enabledSessions = new Map<string, true>()
  constructor(private readonly maxSessions = OPENAI_CODEX_FAST_MODE_MAX_SESSIONS) {
    if (!Number.isSafeInteger(maxSessions) || maxSessions < 1 || maxSessions > OPENAI_CODEX_FAST_MODE_MAX_SESSIONS) {
      throw new RangeError('Fast Mode registry capacity is out of bounds')
    }
  }
  isEnabled(sessionId: unknown): boolean {
    if (!isFastModeSessionId(sessionId)) return false
    const enabled = this.enabledSessions.get(sessionId)
    if (enabled === undefined) return false
    this.enabledSessions.delete(sessionId)   // touch: retain active sessions before eviction
    this.enabledSessions.set(sessionId, true)
    return true
  }
  set(sessionId: unknown, enabled: boolean): void {
    if (!isFastModeSessionId(sessionId)) throw new TypeError('Invalid Fast Mode session id')
    if (typeof enabled !== 'boolean') throw new TypeError('Fast Mode enabled must be boolean')
    if (!enabled) { this.enabledSessions.delete(sessionId); return }
    this.enabledSessions.delete(sessionId)
    while (this.enabledSessions.size >= this.maxSessions) {
      const oldest = this.enabledSessions.keys().next().value as string | undefined
      if (oldest === undefined) break
      this.enabledSessions.delete(oldest)
    }
    this.enabledSessions.set(sessionId, true)
  }
}
```
```ts
// src/adapter.ts — provider decorator
export function withOpenAICodexFastMode(provider: Provider, fastMode: FastModeRegistry | undefined): Provider {
  const streamSimple = provider.streamSimple
  return {
    ...provider,
    streamSimple(model, context: PiContext, options?: SimpleStreamOptions) {
      const enabled = provider.id === OPENAI_CODEX_PROVIDER
        && model.provider === OPENAI_CODEX_PROVIDER
        && fastMode?.isEnabled(options?.sessionId) === true
      if (!enabled) return streamSimple.call(provider, model, context, options)
      const previousOnPayload = options?.onPayload
      return streamSimple.call(provider, model, context, {
        ...options,
        async onPayload(payload, payloadModel) {
          const replaced = await previousOnPayload?.(payload, payloadModel)
          const nextPayload = replaced === undefined ? payload : replaced
          return isPayloadRecord(nextPayload)
            ? { ...nextPayload, service_tier: 'priority' }
            : nextPayload
        },
      })
    },
  }
}
```

**Flow:** validate id → positive-only enable/disable → LRU eviction on overflow (touch-on-read keeps active sessions) → wrapper checks owning provider + enabled session → decorate the (possibly replaced) payload record with `service_tier: 'priority'` while leaving every other field intact.
**Invariant:** a disabled or unknown session is never decorated; a different provider's requests are never decorated even when the registry holds an enabled id; the payload is mutated by merge, never clobbered — an existing `onPayload` replacement is preserved and extended.
**Probe:** `tests/fast-mode.spec.ts` — "defaults off, isolates sessions, deletes on disable, and evicts oldest safely" and "rejects empty, non-string, and overlong opaque session ids"; adapter-boundary tests pin the priority decoration and existing-replacement merge.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", query: "Fast Mode registry session priority service_tier", limit: 20, fields: ["signature", "lines"] });
```

## Verdict
Adopt the bounded positive-only LRU registry and the provider-decorator payload merge (portable, dependency-light, test-pinned). Adapt the session-id source (here it is dsh's opaque session id from `SimpleStreamOptions.sessionId`). Omit the Codex-specific `service_tier: 'priority'` wire value and the `OPENAI_CODEX_PROVIDER` route constant when porting to another provider. Coverage: `src/fast-mode.ts`, `src/adapter.ts`, `tests/fast-mode.spec.ts` all `no_recorded_issue`; the vitest runner is not installed in this read-only checkout, so the deterministic probes were executed against the actual source (Node strip-types) and matched every test assertion.
