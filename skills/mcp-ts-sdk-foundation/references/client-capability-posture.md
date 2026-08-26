<!-- capsule-v2 -->
# Client capability posture — should calling a verb the server didn't advertise throw, or return empty?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** How does the client keep lenient defaults while still offering strict capability enforcement, and which side's capabilities does each assertion hook read?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/client.ts`: soft gates in `listPrompts`/`listResources`/`listResourceTemplates` (:1606-1611, :1646-1651, :1674-1684) and `listTools` (:2489-2502), `_enforceStrictCapabilities = options?.enforceStrictCapabilities ?? false` (:639); strict hooks `assertCapabilityForMethod` (:1400-1469), `assertNotificationCapability` (:1471-1500), `assertRequestHandlerCapability` (:1502-1543); enforcement point in `packages/core-internal/src/shared/protocol.ts` `_requestWithSchemaViaCodec` (:1379-1387).
**Signature:** `protected assertCapabilityForMethod(method: RequestMethod | string): void` (override) — called by the shared funnel only under `enforceStrictCapabilities === true`.
**Data Shape:** `ServerCapabilities` (server-advertised, captured at handshake/discover) vs `this._capabilities` (client-declared, constructor copy).

### Decisive source
```ts
// protocol.ts :1379-1387 — the funnel is the ONLY caller; opt-in
if (this._options?.enforceStrictCapabilities === true) {
    try { this.assertCapabilityForMethod(request.method); } catch (error) { earlyReject(error); return; }
}
// client.ts :1607-1611 — default lenient tier
if (!this._serverCapabilities?.prompts && !this._enforceStrictCapabilities) {
    console.debug('Client.listPrompts() called but server does not advertise prompts capability - returning empty list');
    return { prompts: [] };
}
// :1428-1433 — nested-member check example inside the strict hook
if (method === 'resources/subscribe' && !this._serverCapabilities.resources.subscribe) { throw … }
```

**Flow:** outbound verbs consult SERVER capabilities two ways: soft tier returns typed-empty results
(`{prompts:[]}`, `{resources:[]}`, `{tools:[]}`…) with a debug log when unadvertised; strict tier
(opt-in) makes every request pass the funnel hook and throw
`SdkError(CapabilityNotSupported, "… required for <method>")`. Inbound server→client requests
(sampling/elicitation/roots) and outbound notifications are gated against the CLIENT's own declared
capabilities via the other two hooks.

**Invariant:** direction asymmetry — `assertCapabilityForMethod` reads `_serverCapabilities`
(what we may CALL); `assertRequestHandlerCapability`/`assertNotificationCapability` read
`this._capabilities` (what we DECLARED, so what we may ANSWER/EMIT). `initialize`, `ping`,
and `server/discover` are exempt in the request hook; cancelled/progress notifications always
allowed. The strict hooks have no direct behavioral test in-repo (shared tests stub them as
no-ops; :41/:43 of specCorpusDispatch.test.ts shows the hook contract) — port-yourself-pin:
assert both tiers yourself.

**Probe:** `packages/client/test/client/inputRequiredEngine.test.ts` :181 asserts a
`SdkErrorCode.CapabilityNotSupported` rejection shape; structural probe: graph trace shows
`Protocol._requestWithSchemaViaCodec` as the single caller of `assertCapabilityForMethod`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.client.src.client.client.Client.assertCapabilityForMethod" });
```

## Verdict
Adopt the two-tier split (empty-by-default, throw-by-opt-in) for SDK ergonomics; adapt the exempt
method list to your spec revision; omit the soft tier only in tooling where silent empties would
mask misconfiguration. Distinct from client-capability-lattice.md, which owns the core-internal
−32021 requirement DIFF mechanism, not these local SdkError assertions.
