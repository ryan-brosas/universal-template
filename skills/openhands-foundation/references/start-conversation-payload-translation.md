<!-- capsule-v2 -->
# Start-conversation payload translation — how does a UI adapter map its settings model onto a wire contract without leaking fields across launch paths?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How do you build one conversation-start payload that serves inline agents, server-resolved profiles, and ACP subprocesses — with secrets, client tools, and tags correct in each mode?

## Adapter between App settings and StartConversationPayload
**Path/Symbol:** `src/api/agent-server-adapter.ts` (`buildStartConversationRequest` :1054–1235, `toAppConversation` :317–402, `buildStartConversationRequestWithEncryptedSettings` :1258–1297).
**Signature:** `export function buildStartConversationRequest(options: StartConversationOptions): StartConversationPayload`.
**Data Shape:** Options carry settings + optional `encryptedAgentSettings/encryptedConversationSettings`, `agentProfileId/Kind`, `customSecrets`, `secretsEncrypted`, `runtimeServicesInfo`. Payload is conditional-spread: `{agent_profile_id} XOR {agent_settings}`, plus workspace, `client_tools`, confirmation policy, tags, secrets, etc.

### Decisive source
```ts
// ``agent_profile_id`` and ``agent_settings`` are mutually exclusive agent
// sources; the profile path lets the server resolve the profile (#3727).
//
// Enrichment boundary: on the profile path the server rebuilds the agent
// purely from the stored profile fields, so the client-owned enrichments
// this adapter folds into ``agent_settings`` do NOT apply. …
...(options.agentProfileId
  ? { agent_profile_id: options.agentProfileId }
  : { agent_settings: agentSettings }),
```
```ts
const lookupSecret: LookupSecret = {
  kind: "LookupSecret",
  url: `/api/settings/secrets/${encodeURIComponent(secret.name)}`,
  description: secret.description,
};
if (Object.keys(headers).length > 0) lookupSecret.headers = headers;
```

**Flow:** merge encrypted settings → detect ACP → choose launch kind (profile kind > acp > openhands) → build configured agent/conversation settings → assemble payload with the XOR spread → stamp tags (`CLIENT_SOURCE_TAG_KEY` always; `acpserver` ONLY on inline ACP launches) → gate `secrets_encrypted` (never for pure-ACP unless `mcp_config` carries Fernet MCP secrets) → serialize custom secrets as host-relative LookupSecret URLs with auth headers.
**Invariant:** Secrets travel through exactly ONE channel — `payload.secrets` as `LookupSecret` entries the SERVER resolves from its own store at spawn time — never mirrored into `agent_context.secrets`, uniform for ACP and non-ACP (#1039). `client_tools` attach only when `launchAgentKind === "openhands"` because an ACP subprocess cannot execute browser tools. The agent-server caches client-tool schemas per NAME for process life and rejects differing re-registration (`ClientToolSchemaConflictError`) — schema edits require restarting a long-running dev server.
**Probe:** `__tests__/api/agent-server-adapter.test.ts` — `:473-512` pins LookupSecret shape incl. `folder%2Fname` encoding and `X-Session-API-Key` header; `:561` "request.secrets is the sole channel"; `:662-681` secrets_encrypted ACP matrix; `:731-767` client-tool gating per launch kind.

### Secondary invariants worth porting (read side, `toAppConversation`)
- UI-only fields (selected repo/branch/provider/workspace/profile) hydrate from CLIENT-side stored metadata keyed by conversation id — the wire payload doesn't carry them.
- `acp_server` chip renders only for `isAcp` conversations even if the wire carries a stray tag on an OpenHands conversation (#3692/#1571); metrics prefer backend metrics → `stats.usage_to_metrics` combine → zero snapshot.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "adapter start conversation request toAppConversation", limit: 10, fields: ["signature", "lines"] });
// → buildStartConversationRequest :1054-1235 (180 L), toAppConversation :317-402
```

## Verdict
Adopt the profile-XOR-inline spread, single-channel LookupSecret delivery, launch-kind-gated client tools, and the client-side metadata hydration split. Adapt field names/payload shape to your wire contract. Omit ACP/mcp_config specifics if you have no subprocess-agent mode. Coverage caveat: none recorded at pin; adapter test inventoried (87 cases) with decisive ranges read directly.
