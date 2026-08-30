<!-- capsule-v2 -->
# beta-header sticky latches — why does toggling a mode mid-session silently cost you your prompt cache?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Beta headers and body params are evaluated per request — how do you stop mid-session feature toggles from changing the serialized request shape and busting a 50–70K-token server-side prompt cache?

## afkModeHeaderLatched family: latch-once-per-conversation beta headers
**Path/Symbol:** `src/bootstrap/state.ts`:`afkModeHeaderLatched` (`:226-233`), `fastModeHeaderLatched` (`:230-233`), `cacheEditingHeaderLatched` (`:234-237`), `thinkingClearLatched` (`:238-242`), accessors (`:1708-1738`), `clearBetaHeaderLatches` (`:1740-1749`). Consumer flow documented in existing capsule `references/api-streaming-producer.md` (sticky header latches step of the send pipeline).
**Signature:** getters return `boolean | null` (`null` = not yet triggered); setters take `boolean`; `clearBetaHeaderLatches(): void` resets all four to `null`.
**Data Shape:** Four tri-state latches. Semantics per state: `null` = feature never activated this conversation → header absent; `true` = activated at least once → header ALWAYS sent; (setters only accept activation, so no false state in practice). The `speed` body param itself stays DYNAMIC — only the beta HEADER latches.

### Decisive source
```ts
// :226-233
// Sticky-on latch for AFK_MODE_BETA_HEADER. Once auto mode is first
// activated, keep sending the header for the rest of the session so
// Shift+Tab toggles don't bust the ~50-70K token prompt cache.
afkModeHeaderLatched: boolean | null
// Sticky-on latch for FAST_MODE_BETA_HEADER. Once fast mode is first
// enabled, keep sending the header so cooldown enter/exit doesn't
// double-bust the prompt cache. The `speed` body param stays dynamic.
// :1740-1749
export function clearBetaHeaderLatches(): void {
  STATE.afkModeHeaderLatched = null
  STATE.fastModeHeaderLatched = null
  STATE.cacheEditingHeaderLatched = null
  STATE.thinkingClearLatched = null
}
```

**Flow:** user first enables auto/fast/cached-microcompact/thinking-clear → setter flips that latch true → every subsequent request serializes with the same beta header regardless of whether the mode is currently on → `/clear` and `/compact` call `clearBetaHeaderLatches()` so a FRESH conversation re-evaluates headers from scratch.
**Invariant:** Prompt cache keys include the serialized request shape; flipping an optional beta header off (or on) mid-conversation changes that shape for EVERY subsequent call until the cache expires. The fix is one-directional persistence: latches go `null→true` on first activation and stay true for the conversation lifetime; reset happens ONLY at conversation boundaries (/clear, /compact) — never on toggle-off. Distinguish header (sticky) from payload param (dynamic): keeping `speed` dynamic is safe because it doesn't participate in the same cache-key surface as the beta set.
**Probe:** Deterministic pins: `grep -n 'bust the ~50-70K token prompt cache' src/bootstrap/state.ts` → `228:`; `grep -n 'speed.*stays dynamic\|body param stays dynamic' src/bootstrap/state.ts` → `232:`; `grep -c 'STATE.afkModeHeaderLatched = null' src/bootstrap/state.ts` → `2` (:414 initial + :1745 clear).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "beta header latch prompt cache afkModeHeaderLatched", limit: 10 });
```

## Verdict
Adopt sticky-on beta-header latching keyed to conversation boundaries whenever optional capability flags ride the same cached request shape as your system prompt. Adapt latch count/names and the reset points to your command set. Omit the GrowthBook eligibility twin (`promptCache1hEligible`, separately latched :222-225) unless you also gate TTL variants.
