<!-- capsule-v2 -->
# Grok-build minimal ACP dialect — what does a dialect look like when every mechanism already lives in the shared kernel?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory MCP NOT connected this session → direct source+test read fallback per AGENTS.md. **Question:** can a whole agent dialect be ONE pure-config factory when the ACP kernel owns every mechanism — and what still has to be dialect-specific?

## Pure-config factory over createACP
**Path/Symbol:** `packages/harness-grok-build/src/grok-build-harness.ts` (357L whole-file read; `createGrokBuild` :285–356, `GROK_BUILD_BUILTIN_TOOLS` :59–259), `packages/harness-grok-build/src/index.ts` (10L), test `grok-build-harness.test.ts` (223L whole-file read, 4 cases) + `grok-build-harness.test-d.ts` (36L).
**Signature:** `createGrokBuild(settings?): HarnessV1<typeof GROK_BUILD_BUILTIN_TOOLS>` — a single call to `createACP({...})` with NO custom turn driver, NO bridge code, NO translator.
**Data Shape:** 25 builtin tools as `commonTool(nativeName, {...})` / raw `tool({...})` entries with `z.looseObject` input schemas; source pinning as `{ type: 'npm-locked', packageJson, pnpmLockYaml }` embedded via build-time constants (`__GROK_BUILD_IMPLEMENTATION_PACKAGE_JSON__` / `__GROK_BUILD_IMPLEMENTATION_PNPM_LOCK_YAML__`).

### Decisive source
```ts
// grok-build-harness.ts :285–356 — the whole dialect, abridged to its decisions
return createACP({
  auth: settings.auth,
  modelId: settings.model, port: settings.port, portEndpoint: settings.portEndpoint,
  startupTimeoutMs: settings.startupTimeoutMs, mcpServers: settings.mcpServers,
  mintBridgeToken: settings.mintBridgeToken,
  isMcpToolCall: toolCall => {
    const metadata = toolCall._meta?.['x.ai/tool'];
    return isRecord(metadata) && metadata.namespace === 'mcp';   // dialect-specific MCP classification
  },
  version: 'v1', harnessId: 'grok-build',
  builtinTools: GROK_BUILD_BUILTIN_TOOLS,                        // 25 tools, captured schemas
  clientApp: { name: clientAppSegments.join('/'), version: clientAppVersion },
  source: { type: 'npm-locked', packageJson: ..., pnpmLockYaml: ... },  // exact-implementation pin
  executable: 'grok', args: ['agent', 'stdio'],
  credentialEnv: ['XAI_API_KEY'],
  credentialBrokering: ({ env }) => {
    if (!env.XAI_API_KEY) return [];                             // absent key ⇒ NO transformation
    return [createCredentialRequestTransformation({
      baseUrl: env.GROK_XAI_API_BASE_URL ?? 'https://api.x.ai/v1',
      headers: { Authorization: `Bearer ${env.XAI_API_KEY}` },
    })];
  },
  instructionMapping: { type: 'session-meta', path: ['rules'] },
  outputSchemaMapping: { type: 'session-prompt-meta', path: ['outputSchema'] },
  providerAuthentication: { gateway: { env: {
    GROK_CLIENT_NAME: { $source: 'client-app-name' },
    GROK_CLIENT_VERSION: { $source: 'client-app-version' },
    XAI_API_KEY: { $source: 'gateway-api-key' },
    GROK_XAI_API_BASE_URL: { $source: 'gateway-base-url', ensureSuffix: '/v1' },
    GROK_MODELS_BASE_URL: { $source: 'gateway-base-url', ensureSuffix: '/v1' },
  }}},
});
```

**Flow:** everything behavioral — turn pumping, stream translation, host-tool correlation, permissions, lifecycle, stream capture, stderr sentinel, diagnostics, instruction delivery, protocol negotiation, env envelope — is owned by the pass-20/22/28 ACP capsules; the dialect file contributes only DATA and four dialect-specific decisions: (1) the builtin-tool INVENTORY with native names and loose schemas "captured from the model request produced by @xai-official/grok 0.2.111, the version used by the pinned Grok Build ACP implementation" (comment :53–55) — including families no other dialect exposes (spawn_subagent with capability_mode/isolation/resume_from, scheduler_create/delete/list, workflow with agent_budget, image/video generation, ask_user_question, enter/exit_plan_mode); (2) MCP classification by `_meta['x.ai/tool'].namespace === 'mcp'` (the only dialect that needs a predicate — the shared kernel's default cannot know xAI's metadata convention); (3) npm-locked source pinning so the sandbox installs EXACTLY the pinned implementation (test asserts `pnpmLockYaml` contains `'@xai-official/grok@0.2.111'`); (4) a credential-brokering callback that returns `[]` when `XAI_API_KEY` is absent — brokering configured but inert without a key, versus throwing. The test is a full inline-snapshot over the ENTIRE createACP settings object (tool-name list, clientApp, source with parsed package.json, providerAuthentication env map) plus a broker-output equality check (`match: {host: 'api.x.ai', path: {startsWith: '/v1'}}`) and a settings-forwarding case — the snapshot IS the dialect contract.
**Invariant:** a minimal dialect must still pin its implementation (npm-locked source), declare its tool inventory against the pinned version's actual model requests, and classify its MCP calls — config alone cannot express those; everything else is kernel-owned. `credentialEnv` and `credentialBrokering` must be configured together (acp-v1-harness.ts :137–142 throws otherwise — pass-20 capsule).
**Probe:** direct test `grok-build-harness.test.ts` 223L read whole-file (4 cases: enforcement snapshot, settings forwarding, MCP classification true/false, test version). Deterministic probes: `grep -c "commonTool(" packages/harness-grok-build/src/grok-build-harness.ts` → `5`; `grep -n "x.ai/tool" packages/harness-grok-build/src/grok-build-harness.ts` → :279; `grep -n "@xai-official/grok@0.2.111" packages/harness-grok-build/src/grok-build-harness.test.ts` → :33.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createGrokBuild grok build ACP builtin tools harness", limit: 10 });
```
Graph MCP absent this session — file-level analog: naive "grok" queries hit only xAI provider-package symbols (packages/xai), zero harness-dialect hits; GREEN: `createGrokBuild` resolves to exactly one defining file (:262) and its snapshot test.

## Verdict
Adopt: the pure-config factory shape for any runtime that speaks your host protocol natively — spend code only on tool inventory fidelity, implementation pinning, MCP classification, and credential brokering. Adapt the tool inventory to YOUR pinned runtime's actual request shapes (capture, do not guess). Omit nothing from the four decisions — they are the irreducible dialect surface.
