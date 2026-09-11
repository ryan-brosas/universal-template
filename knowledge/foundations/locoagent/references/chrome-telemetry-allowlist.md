<!-- capsule-v2 -->
# Telemetry allowlist bridge — how do you let a vendored MCP server emit analytics when page content could leak into string fields?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the safe metadata contract for third-party-sourced events, including reserved-field collisions?

## chrome-telemetry-allowlist
**Path/Symbol:** `src/utils/claudeInChrome/mcpServer.ts` (`SAFE_BRIDGE_STRING_KEYS` :30-34, `trackEvent` :218-244).
**Signature:** `trackEvent(eventName: string, metadata?: Record<string, unknown>): void` — filters then forwards to host `logEvent`.
**Data Shape:** booleans/numbers pass through; strings ONLY when the key ∈ {`bridge_status`, `error_type`, `tool_name`}; key `status` renamed to `bridge_status`; values cast to the host's `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` type.

### Decisive source
```ts
// String metadata keys safe to forward to analytics. Keys like error_message
// are excluded because they could contain page content or user data.
const SAFE_BRIDGE_STRING_KEYS = new Set([
  'bridge_status',
  'error_type',
  'tool_name',
])
```
```ts
// Rename 'status' to 'bridge_status' to avoid Datadog's reserved field
const safeKey = key === 'status' ? 'bridge_status' : key
```

**Flow:** the chrome-mcp package emits events with arbitrary metadata (may include error messages containing page text) → this adapter drops every string field not on the three-key allowlist, renames the colliding key, and forwards only scalars + vetted strings → host analytics pipeline receives privacy-safe payloads.
**Invariant:** an allowlist (not denylist) is mandatory because the producer is OUTSIDE your trust boundary — new unsafe fields default to dropped; reserved-backend-field collisions must be renamed at the adapter, not negotiated with the backend.
**Probe:** no upstream test. Deterministic pins: `grep -n "page content" src/utils/claudeInChrome/mcpServer.ts` → :28-29; `grep -n "reserved field" src/utils/claudeInChrome/mcpServer.ts` → :228.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "trackEvent SAFE_BRIDGE_STRING_KEYS", limit: 10 });
```

## Verdict
Adopt the allowlist+rename adapter for untrusted event producers. Adapt the key set. Omit the analytics backend specifics. Coverage caveat: no unit tests upstream.
