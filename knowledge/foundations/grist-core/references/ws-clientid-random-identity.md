<!-- capsule-v2 -->
# ws-clientid-random-identity — Why are clientIds random hex rather than sequential, and why does a Client carry TWO ids?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What breaks if clientIds are predictable, and what is publicClientId for?

## generateClientId + dual-id split
**Path/Symbol:** `app/server/lib/Client.ts:generateClientId` (:44–57), assigned in constructor :127–128; `clientId` (confidential) vs `publicClientId` (distributable) :79–82.
**Signature:** `function generateClientId(): string { return crypto.randomBytes(8).toString("hex"); }`.
**Data Shape:** 16-hex-char random string; clientId = backend↔browser-window identity used in reconnect params; publicClientId = safe to embed in shared/exported artifacts.

### Decisive source
```ts
/**
 * Generates and returns a random string to use as a clientId. This is better
 * than numbering clients with consecutive integers; otherwise a reconnecting
 * client presenting the previous clientId to a restarted (new) server may
 * accidentally associate itself with a wrong session that happens to share the
 * same clientId. In other words, we need clientIds to be unique across server
 * restarts.
 */
function generateClientId(): string {
  // Non-blocking version of randomBytes may fail if insufficient entropy is
  // available without blocking. If we encounter that, we could either block,
  // or maybe use less random values.
  return crypto.randomBytes(8).toString("hex");
}
```

**Flow:** every new Client draws TWO independent random ids → clientId lives in sessionStorage and rides reconnect URLs → after a server RESTART, a stale presented id cannot collide with any live Client (fresh random space) ⇒ reuse gate fails safely into a fresh Client instead of hijacking a stranger's session → publicClientId travels where the confidential one must not.
**Invariant:** uniqueness must hold ACROSS restarts, not just within a process — sequential counters reset on restart and would re-bind old ids to new sessions. The comment also flags the entropy tradeoff (non-blocking randomBytes can fail under pressure; blocking or weaker fallbacks named as alternatives). The two-id split keeps log/telemetry surfaces free of the credential-adjacent id.
**Probe:** deterministic source pins only (generator untested directly — coverage caveat recorded); cross-restart safety exercised indirectly by the identity-reuse matrix `test/server/Comm.ts:1233+`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "generateClientId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt crypto-random client/session ids with explicit across-restart uniqueness rationale; adopt the confidential/public split when ids leave the process boundary. Adapt length/entropy to your threat model.
