<!-- capsule-v2 -->
# ACP turn-start config fingerprint — how do you prove persisted recovery config still matches current settings without persisting secrets?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** How can a respawned process verify "the world that created this state is the same as mine" when credentials rotate between processes?

## Sorted-key SHA-256 over non-secret configuration only
**Path/Symbol:** `packages/harness-acp/src/v1/acp-v1-turn-start-config.ts` — `createACPTurnStartConfig` (:19–77), `createACPColdSessionState` (:79–103), `sortValue` (:109–121); revalidation in `acp-v1-harness.ts:1607–1699`.
**Signature:** `createACPTurnStartConfig({prompt, tools, builtinTools, permissionMode, permissionModeMapping, mcpServers, debug, authenticationProfile, sessionMeta, instructionMapping, responseFormat, outputSchemaMapping}): ACPTurnStartConfig`.
**Data Shape:** output carries `version:1`, `configurationFingerprint` (hex), plus verbatim copies of prompt blocks and zod-parsed tool specs; cold state = same fingerprint + tools/builtinTools/permissionMode/responseFormat/mappings + `modelId`, MINUS prompt.

### Decisive source
```ts
// acp-v1-turn-start-config.ts:46–62 — hash ONLY non-secret config, key-sorted
configurationFingerprint: createHash('sha256')
  .update(stableStringify({
    authenticationProfile,          // the DIGEST identity, never raw credentials
    sessionMeta: sessionMeta ?? null,
    ...(instructionMapping == null ? {} : { instructionMapping }),
    ...(outputSchemaMapping == null ? {} : { outputSchemaMapping }),
    builtinTools,
    permissionModeMapping: permissionModeMapping ?? null,
    mcpServers: mcpServers ?? null,
  }))
  .digest('hex'),
prompt: [...prompt],
tools: tools.map(tool => acpSerializableToolSpecSchema.parse(tool)), // zod at the boundary
...
// acp-v1-harness.ts:1626–1647 — validate-by-RECOMPUTE, not by trusting stored bytes
const current = createACPTurnStartConfig({
  prompt: turnStartConfig.prompt, tools: turnStartConfig.tools,
  /* every OTHER field taken from CURRENT settings */
});
if (current.configurationFingerprint !== turnStartConfig.configurationFingerprint) {
  throw new Error('The persisted ACP turn start configuration is incompatible with the current non-secret start configuration.');
}
```

**Flow:** each `doPromptTurn` builds a fresh config (fingerprint over non-secret axes; prompt+tools carried alongside) → stored into lifecycle state on suspend/detach → on lossy-rerun/cold-restore recovery the harness rebuilds a config from PERSISTED prompt/tools but CURRENT auth profile, mappings, mcpServers → fingerprint inequality throws before any frame is sent. Cold validation additionally compares `permissionMode` and `modelId` literally (:1690–1697). Key-sorted recursive stringify makes JSON key order irrelevant to equality.
**Invariant:** secrets (gateway keys, clientApp identity, resolved env) are excluded from the hashed payload BY CONSTRUCTION, so the persisted state can never leak them while still detecting any drift in settings that would change runtime behavior — and validation always recomputes rather than re-hashing untrusted stored bytes.
**Probe:** direct test `packages/harness-acp/src/acp-harness.test.ts:2134–2180` ("rejects cold lifecycle state when the configured model changes" — same harness id, different modelId ⇒ 'ACP cold-session state is incompatible…'), :2465–2597 (lossy-rerun start frame carries original prompt but asserts NOT-contains both old AND new gateway secrets), :3597–3658 (implementation-args change ⇒ rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createACPTurnStartConfig createACPColdSessionState stableStringify configurationFingerprint", limit: 10 });
```

## Verdict
Adopt validate-by-recompute fingerprints over non-secret config axes for any durable recovery envelope; adapt which fields count as behavior-relevant (modelId/permissionMode literal compares here); omit ACP tool-spec schema. Caveat: no dedicated acp-v1-turn-start-config.test.ts exists at this pin — behavior pinned indirectly through adapter-level rejection cases.
