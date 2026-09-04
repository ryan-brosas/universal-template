<!-- capsule-v2 -->
# ACP protocol configuration + bridge environment envelope — how do you negotiate a protocol with a spawned agent and carry credentials to it through one env var?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The bridge is a separate process spawned beside an ACP agent. It must (a) build the initialize request with the right capabilities, (b) resolve gateway credentials into the agent's launch environment, (c) verify the agent did not silently downgrade the protocol or skip authentication, and (d) receive its whole configuration from the parent through the process environment. How do the four pieces fit?

## Exact-match negotiation + one-var zod envelope
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/protocol-configuration.ts` — `createACPInitializeRequest` (:15–52), `resolveACPLaunchEnvironment` (:54–76), `validateACPProtocolVersion` (:78–90), `assertACPAuthenticationMethod` (:92–106), `mergeRecords` (:108–122); `packages/harness-acp/src/v1/bridge/acp-v1-bridge-environment.ts` — `ACP_BRIDGE_CONFIGURATION_ENV` (:8), `profileValueSchema` z.lazy union (:12–35), `createACPBridgeEnvironment` (:71–85), `readACPBridgeEnvironment` (:87–99); wiring `acp-v1-harness.ts` :553–561 (parent serializes), `bridge/index.ts` :82 (child reads), :440–456 (initialize + version validate), :653–668 (auth method assert inside authenticate).
**Signature:** `createACPInitializeRequest({ protocolVersion, clientApp, authentication, supportsBooleanSessionConfigOptions = false })`; `resolveACPLaunchEnvironment({ providerAuthentication, gateway }): Record<string, string>`; `createACPBridgeEnvironment(ACPBridgeConfiguration): Record<string, string>`; `readACPBridgeEnvironment({ env }): Promise<ACPBridgeConfiguration>`.
**Data Shape:** the envelope var `AI_SDK_ACP_BRIDGE_CONFIGURATION` carries `{authentication?, providerAuthentication?, providerEnvironment?, sessionMeta?}` where providerAuthentication is a discriminated union (`direct` | `ai-gateway` with a profile-value record). Profile values are scalars, `$source` placeholder objects (`gateway-api-key`/`gateway-base-url`/`gateway-authorization`/`client-app`/`client-app-name`/`client-app-version`, each with optional prefix/suffix/ensureSuffix), or recursive arrays/records.

### Decisive source
```ts
// protocol-configuration.ts:78–90 — no downgrade tolerance, no silent auth skip
export function validateACPProtocolVersion({ requested, initialization }): void {
  if (initialization.protocolVersion !== requested) {
    throw new Error(
      `ACP protocol negotiation failed: requested v${requested}, agent selected v${initialization.protocolVersion}.`,
    );
  }
}
// acp-v1-bridge-environment.ts:87–99 (abridged) — fail-closed read, no content echo
const serialized = env[ACP_BRIDGE_CONFIGURATION_ENV];
if (serialized == null) return {};
try {
  const result = bridgeConfigurationSchema.safeParse(JSON.parse(serialized));
  if (result.success) return result.data;
} catch {}
throw new Error('ACP bridge configuration environment is invalid.');
```

**Flow:** parent side — the harness resolves provider authentication, serializes the whole bridge configuration into the one env var, and spawns the bridge child with it (plus channel token/port). Child side — `readACPBridgeEnvironment` parses the var (absent ⇒ empty config; invalid ⇒ fixed-message throw without echoing contents); `createACPInitializeRequest` builds clientInfo from the required client-app env values and merges a `session.configOptions.boolean: {}` capability ONLY when the start config maps some permission mode to a boolean session-config option (computed at the call site from `permissionModeMapping`); `resolveACPLaunchEnvironment` resolves `$source` placeholders against the bridge's own gateway env (required when provider auth is ai-gateway — `requireGateway` throws otherwise), JSON-stringifying non-string values; non-gateway auth ⇒ empty env (providerEnvironment, when supplied directly, bypasses resolution entirely). After the initialize response: exact version match, then `authenticate` asserts the configured methodId is among the agent's ADVERTISED auth methods before requesting it.
**Invariant:** the child never trusts unvalidated env — the zod schema (with the recursive `z.lazy` profile-value union) is the only path from environment to configuration; negotiation is exact-match (an agent that answers v2 to a v1 request fails the turn rather than being driven against a mismatched dialect); authentication is asserted against the agent's own advertisement, not assumed; capability merging is deep (records merge recursively, scalars overwrite) so a configured `_meta`-bearing capability survives the boolean-option merge; gateway values are required exactly when needed (ai-gateway provider auth) and never resolved speculatively.
**Probe:** `bridge/protocol-configuration.test.ts` (171L, 6 cases) — v1 negotiation with no invented capabilities, gateway env resolution incl. `ensureSuffix` and non-string JSON serialization, client-attribution headers inside structured CODEX_CONFIG, boolean-capability deep merge preserving `_meta`, version/auth-method failure messages. `bridge/acp-v1-bridge-environment.test.ts` (92L, 5 cases) — full round-trip incl. all five `$source` kinds, absent-var ⇒ {}, gateway launch-env round-trip, secret-safety throw, schema-mismatch rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createACPInitializeRequest resolveACPLaunchEnvironment readACPBridgeEnvironment validateACPProtocolVersion AI_SDK_ACP_BRIDGE_CONFIGURATION", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-env-var zod envelope for any parent→sandboxed-child configuration handoff (one variable, schema-validated on read, absent ⇒ defaults, invalid ⇒ fixed message without content echo) — it beats scattering dozens of env vars whose shapes drift; adopt exact-match protocol validation and advertisement-checked authentication for any negotiated protocol where a silent downgrade or skipped auth would corrupt the session invisibly; adopt call-site-conditional capability merging (declare a capability only when a feature is actually configured). Adapt the `$source` placeholder vocabulary to your credential sources; omit the launch-env resolution where the agent reads credentials from the protocol itself. Coverage caveat: both files fully test-pinned (11 cases combined); the parent-side serialization wiring (acp-v1-harness :553) is deterministic-read-only.
