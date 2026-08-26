<!-- capsule-v2 -->
# Auth-seam provenance stamp — how do you classify an error's ORIGIN when error types are unreliable across bundles?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Downstream routing (probe → auth recovery vs era verdict) needs to know "did this error escape an auth seam?" — how is that provenance recorded so it survives bundling?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/authSeam.ts`: `markAuthSeamEscape` (:23-33), `isAuthSeamEscape` (:35-40), `AUTH_SEAM = Symbol.for('mcp.authSeamEscape')` (:21); consumers: `normalizeReply` send-error branch (versionNegotiation.ts :395-411), transport auth seams (token() read, onUnauthorized, 403 step-up).
**Signature:** `markAuthSeamEscape<T>(error: T): T` — identity-preserving; `isAuthSeamEscape(error: unknown): boolean`.
**Data Shape:** Stamp = own symbol-keyed property `true`. `Symbol.for` global registry ⇒ the SAME symbol resolves across duplicated SDK copies in one process (bundler double-install, version skew) and across realms.

### Decisive source
```ts
export function markAuthSeamEscape<T>(error: T): T {
    if ((typeof error === 'object' && error !== null) || typeof error === 'function') {
        try { Object.defineProperty(error, AUTH_SEAM, { value: true, configurable: true }); }
        catch { /* Frozen/sealed: leave unstamped. */ }
    }
    return error;
}
```

**Flow:** any throw crossing a transport auth seam is stamped AT THE THROW BOUNDARY → probe wiring checks `isAuthSeamEscape(e) || e instanceof UnauthorizedError || e.name === 'UnauthorizedError'` (brand/name fallback for foreign transports and differently-bundled copies) ⇒ classified auth-required, propagated UNCHANGED for finishAuth() → everything else falls to network-error classification.

**Invariant:** Provenance is recorded where it is KNOWN, never reconstructed downstream from error types (a TypeError from DCR and one from CORS are indistinguishable by type). Frozen/sealed objects are returned unstamped rather than replaced — identity outranks provenance; primitives cannot carry the stamp. Foreign-transport contract pairs the stamp with name-based UnauthorizedError recognition because a differently-bundled class fails `instanceof`.

**Probe:** `packages/client/test/client/probeAuthSeam.test.ts` :212 ("token() throws at the _commonHeaders read — browser: raw TypeError propagates, never the CORS-legacy verdict"), :233 ("a CUSTOM onUnauthorized callback throws TypeError — raw propagation").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "markAuthSeamEscape isAuthSeamEscape", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt throw-boundary Symbol.for stamps whenever origin must survive rethrow chains; adapt seam list to your transport; omit instanceof/name fallbacks if you control all throwers.
