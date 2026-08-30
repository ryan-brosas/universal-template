<!-- capsule-v2 -->
# Dialect auth resolver ladder — how do you resolve provider credentials into an env blob ONCE with a mode ladder that survives five runtimes and a legacy option shape?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory MCP NOT connected this session → direct source+test read fallback per AGENTS.md. **Question:** how do you resolve provider credentials into the env-var blob a sandbox bridge needs, with an explicit-mode-over-ambient-detection ladder, when five runtimes disagree on providers, base-URL shapes, and option ergonomics?

## Two-function family, one skeleton
**Path/Symbol:** `packages/harness-cline/src/cline-auth.ts` (`resolveClineEnv` :7–27), `packages/harness-codex/src/codex-auth.ts` (`resolveCodexEnv` :70–95, `resolveCodexAuthenticationMode` :97–107, `toCodexGatewayBaseUrl` :198–201), `packages/harness-claude-code/src/claude-code-auth.ts` (`resolveClaudeCodeEnv` :87–118, `resolveClaudeCodeAuthenticationMode` :120–130, `pickAnthropic` :158–178, `pickGateway` :215–231), `packages/harness-opencode/src/opencode-auth.ts` (`resolveOpenCodeEnv` :138–190, `resolveOpenCodeAuthenticationMode` :192–216, `resolveOpenCodeProvider` :99–108, `resolveOpenCodeAuthenticationMode` :177–216, `toOpenCodeGatewayBaseUrl` :311–314), `packages/harness-deepagents/src/deepagents-auth.ts` (`resolveDeepAgentsEnv` :65–88, `resolveDeepAgentsAuthenticationMode` :92–100).
**Signature:** `resolve<Name>Env(auth, processEnv) => Record<string, string>`; `resolve<Name>AuthenticationMode(auth, processEnv) => 'direct' | 'ai-gateway' | <provider>`; consumption: `create<Name>RequestTransformations(env, mode)` → `sandboxSession.addRequestTransformations(...)` (claude-code-harness.ts :847–875, codex-harness.ts :239–258, opencode-harness.ts :270–291, deepagents-harness.ts :235–255).
**Data Shape:** the env blob mixes credential values (`*_API_KEY`, `ANTHROPIC_AUTH_TOKEN`) with routing values (`*_BASE_URL`); the resolved mode is a SEPARATE return because the transformation factory needs it to choose the base URL when the env blob has none.

### Decisive source
```ts
// codex-auth.ts :73–95 — the ladder in its purest form
export function resolveCodexEnv(auth, processEnv = process.env) {
  const normalizedAuth = normalizeCodexAuthToLegacyAuth(auth);
  if (normalizedAuth?.openaiCompatible) {                       // 1. custom endpoint
    return pickOpenAICompatible(normalizedOpenaiCompatible, processEnv);
  }
  if (normalizedAuth?.openai) {                                 // 2. explicit direct
    return pickOpenAI({ explicit: normalizedAuth.openai, processEnv });
  }
  const gatewayAuthFromEnv = getAiGatewayAuthFromEnv({ env: processEnv });
  if (normalizedAuth?.gateway) {                                // 3. explicit gateway
    return pickGateway({ explicit: normalizedAuth.gateway, gatewayAuthFromEnv });
  }
  if (gatewayAuthFromEnv.apiKey) {                              // 4. ambient gateway
    return pickGateway({ explicit: {}, gatewayAuthFromEnv });
  }
  return pickOpenAI({ processEnv });                            // 5. ambient direct
}
```

**Flow:** every dialect normalizes its options FIRST (`normalize<Name>AuthToLegacyAuth` — string modes map to empty explicit objects, `undefined`/`'auto'` to `undefined`, legacy objects to themselves plus a `console.warn('[<name>] Passing an object to auth options is deprecated...')`), then walks explicit-mode rungs before ambient detection; ambient detection always consults `getAiGatewayAuthFromEnv` (which accepts `AI_GATEWAY_API_KEY` or `VERCEL_OIDC_TOKEN`) BEFORE direct provider keys, so a gateway key silently wins over a coexisting direct key unless the direct mode is explicit (test-pinned per dialect: claude-code-auth.test.ts "preserves explicit Anthropic auth despite ambient Gateway credentials", codex "preserves direct auth despite ambient Gateway credentials", opencode "preserves explicit selected-provider auth despite ambient Gateway credentials"). Explicit selection with NO credentials does NOT fall back — cline pins gateway mode to a bare `AI_GATEWAY_BASE_URL` with no key (cline-auth.test.ts "pins explicit Gateway mode without falling back to a direct key"); pi's explicit `ai-gateway` without creds returns `{}` and registers NOTHING (pi-auth.test.ts "registers nothing when ai-gateway mode has no gateway credentials"). Divergences: opencode selects its direct provider from the MODEL STRING (`resolveOpenCodeProvider` — explicit `provider` param, else `model.split('/')[0]` when it is `openai`/`anthropic`, else default `anthropic`) and supports an `openaiCompatible` escape hatch serialized through `OPENAI_QUERY_PARAMS_JSON`; codex aliases `OPENAI_API_KEY ?? CODEX_API_KEY` into `CODEX_API_KEY` and forces gateway base URLs to end in `/v1` (`toCodexGatewayBaseUrl` — trailing-slash strip then suffix append); opencode does the same `/v1` forcing; deepagents instead STRIPS trailing slashes and keeps the gateway at its ROOT because "the Anthropic SDK appends `/v1/messages`, so the gateway base stays at its root" (deepagents-auth.ts pickGateway comment, test "routes through the gateway anthropic endpoint (no /v1 suffix)"); claude-code forwards `ANTHROPIC_BASE_URL` as-is. Codex wiring wrinkle (codex-harness.ts :260–270): when brokering is active in direct mode with no explicit base URL, the SANDBOX env gets `OPENAI_BASE_URL = DEFAULT_OPENAI_BASE_URL` materialized — "Materializing Codex's standard OpenAI URL makes the bridge select its custom provider, where WebSockets are disabled, while keeping the non-brokered path on Codex's built-in OpenAI provider." Deepagents is Anthropic-only by design: "Non-Anthropic models reach it through AI Gateway's Anthropic-compatible endpoint" (deepagents-auth.ts comment above `resolveDeepAgentsEnv`).

**Invariant:** resolution happens ONCE per `doStart` on the host; the resolved blob feeds BOTH the real-credential transformation (host-side) and the masked spawn env (name-placeholder values via `maskSandboxCredentials` over the dialect's `*_CREDENTIAL_ENVIRONMENT_VARIABLES` const tuple — pass-22 brokering capsule owns that half); explicit selection never silently falls back; ambient gateway beats ambient direct; legacy object options warn but keep working.

**Probe:** deterministic probes executed at pin: `grep -c "getAiGatewayAuthFromEnv" packages/harness-codex/src/codex-auth.ts` → `2` (resolve + mode); `grep -n "preserves explicit Anthropic auth despite ambient" packages/harness-claude-code/src/claude-code-auth.test.ts` → :229; `grep -n "no /v1 suffix" packages/harness-deepagents/src/deepagents-auth.test.ts` → :34; `grep -n "OPENAI_QUERY_PARAMS_JSON" packages/harness-opencode/src/opencode-auth.ts` → :262/:265. Direct tests read whole-file: cline-auth.test.ts 88L (6 cases), codex-auth.test.ts 212L (17 cases), claude-code-auth.test.ts 249L (19 cases), opencode-auth.test.ts 238L (13 cases), deepagents-auth.test.ts 188L (13 cases).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "resolveCodexEnv resolve gateway auth from env authentication mode ladder dialect", limit: 10 });
```
Graph MCP absent this session — file-level analog executed instead: naive query terms ("auth", "resolve env") localize nothing among 70 packages without the `resolve<Name>Env` vocabulary; GREEN: each cited symbol resolves to exactly one DEFINING file at the recorded line anchors (verified by direct read at pin).

## Verdict
Adopt: the two-function split (env blob + resolved mode), normalize-then-ladder ordering, ambient-gateway-over-direct precedence, explicit-no-fallback pinning, per-runtime base-URL shape as an EXPLICIT documented divergence. Adapt provider sets and env names to your runtimes. Omit the Vercel gateway defaults and the legacy-object deprecation shim if you have no API-stability constraint.
