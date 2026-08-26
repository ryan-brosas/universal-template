<!-- capsule-v2 -->
# Legacy input_required shim — how does a 2025-era server emulate multi-round-trip flows for old clients?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When the server can't send embedded input requests in-band (legacy wire), how does it run the same multi-round-trip flow through per-request transports?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/legacyInputRequiredShim.ts`: `LegacyInputRequiredShim` class (:160+), `resolveLegacyShimOptions` (:61-79), `coerceEmbeddedInputRequest` (:91-147), host interface (:149-158); shared primitives `sleep`/`linkedRoundAbort`/`inputRequiredRoundsExceededMessage` imported from the client-side driver module (pacing/abort semantics must MATCH per era).
**Signature:** `coerceEmbeddedInputRequest(entry: unknown): CoercedEmbeddedInputRequest | undefined` — accepts both bare result shapes and `{method, result}` wrapped envelopes (the mirror image of the client's partition rule).
**Data Shape:** The shim re-issues each embedded input request as its own legacy JSON-RPC request over the session, collects responses, and folds them into a retry carrying `inputResponses` — emulating what the modern era does in-band.

### Decisive source
```ts
// One formatter so the texts cannot drift (hosts and models read the
// tool-result copy verbatim).
export function inputRequiredRoundsExceededMessage(method: string, maxRounds: number): string {
    return `Multi-round-trip request '${method}' still required input after ${maxRounds} rounds (inputRequired.maxRounds)`;
}
// Shared with the client driver: the pacing semantics must match per era.
export function sleep(ms: number, signal: AbortSignal | undefined): Promise<void> { … }
```

**Flow:** handler returns an input-required payload on the legacy leg → shim resolves options → coerces embedded entries (bare OR wrapped) → dispatches each as a standalone request to the client → collects bare responses → retry with accumulated `inputResponses` under the shared round cap/pacing/abort-linkage → complete result surfaces normally; cap exceeded ⇒ the SAME formatted failure text the modern client emits.

**Invariant:** Cross-era behavioral parity is maintained by SHARING primitives (sleep, abort linkage, message formatter) between the client driver and this shim — divergent pacing or failure copy would make hosts' tool-result parsing era-dependent. Coercion asymmetry is deliberate: the server ACCEPTS wrapped envelopes that the client-side partition DROPS (each side mirrors its peer population).

**Probe:** coverage caveat: no dedicated direct suite at this pin; shared-primitive parity pinned via `packages/client/test/client/inputRequiredEngine.test.ts` (same sleep/linkage/formatter symbols).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "LegacyInputRequiredShim coerceEmbeddedInputRequest resolveLegacyShimOptions", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt shared-primitive cross-era emulation only when you must serve MRTR to pre-in-band clients; adapt coercion rules to your client population; omit entirely on modern-only deployments.
