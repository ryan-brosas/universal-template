<!-- capsule-v2 -->
# Valueless diagnostics — log the decision inputs as booleans and counts, never the credential values

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When an auth gate's failure is only diagnosable from its decision inputs, how do you log enough to diagnose without ever writing a credential to disk?

## Path/Symbol
**Path:** `src/runtime.ts` (`resolveModel` rejection/acceptance logging **:192-211**); helpers `countHeaders` **:26-28**, `countUsableHeaders` **:31-36**.
**Symbol:** debug events `resolve.rejected`, `resolve.request_time_signing`.

**Signature:**
```ts
function countHeaders(headers: unknown): number        // Object.keys().length when object else 0 — ALL headers
function countUsableHeaders(headers: unknown): number  // values that are non-empty strings — the ones the host could actually send
```

**Data Shape:** NDJSON debug-log entries `{ event: "resolve.rejected" | "resolve.request_time_signing", data: { provider, reason?, authOk, hasApiKey, resolvedEmptyApiKey, headerCount, usableHeaderCount, isOAuth, providerCredentialConfigured, signsAtRequestTime } }`.

### Decisive source
```ts
// The reason string alone cannot tell `ok:false` from `ok:true` with nothing to
// carry, which is what made the ambient-credential outage un-diagnosable from the
// debug log. Record the decision inputs — booleans and counts only, never values.
debugLog("resolve.rejected", {
    provider, reason,
    authOk: auth.ok === true,
    hasApiKey: typeof auth.apiKey === "string" && auth.apiKey.length > 0,
    resolvedEmptyApiKey,
    headerCount: countHeaders(auth.headers),
    usableHeaderCount: countUsableHeaders(auth.headers),
    isOAuth, providerCredentialConfigured, signsAtRequestTime,
});
...
if (!usable) {
    debugLog("resolve.request_time_signing", { provider, providerCredentialConfigured });
}
```

**Flow:** on rejection → emit `resolve.rejected` with the full input vector; on acceptance of a request-time-signed provider (nothing usable but accepted) → emit the single-line `resolve.request_time_signing`; a normal usable-auth resolve logs NOTHING (the debug plane is fail-open silent by design).

**Invariant:** The ambient-credential outage was invisible for eight weeks because the only breadcrumb read identically for `auth.ok:false` and `auth.ok:true`+empty. Two rules make this class diagnosable:
1. **Booleans and counts, never values** — `headerCount` vs `usableHeaderCount` distinguishes "header present but empty string" (`{Authorization:""} → 1 vs 0`) from no header at all; `hasApiKey` is existence-not-value; a dedicated test greps the whole log file and fails if any credential material appears.
2. **Log the ACCEPTANCE path too** — without `resolve.request_time_signing`, a working ambient host is indistinguishable from one where the gate silently did something surprising.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "resolve.rejected" src/runtime.ts        # expect 1 && \
grep -c "resolve.request_time_signing" src/runtime.ts   # expect 1 && \
npx vitest run tests/resolve-diagnostics.test.ts # 4 passed incl. the secret-leak grep
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "countUsableHeaders resolve.rejected debugLog resolve.request_time_signing", limit: 5 });
// rank1: ...tests.resolve-diagnostics.test.resolve Function tests/resolve-diagnostics.test.ts 44-50 (diagnostics plane; countUsableHeaders sits at src/runtime.ts 31-36)
```

**Verdict:** Adopt boolean/count decision-input logging with a hard no-values rule plus an explicit acceptance-path event. Adapt event names to your debug plane. Omit nothing.
