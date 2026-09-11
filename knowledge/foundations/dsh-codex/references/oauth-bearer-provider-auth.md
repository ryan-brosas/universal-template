<!-- capsule-v2 -->
# OAuth bearer provider auth — how do you feed a subscription OAuth token to a generic adapter expecting API keys, with no environment/API-key discovery and fail-the-request-on-empty semantics?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How do you feed a subscription OAuth token to a generic adapter expecting API keys, with no environment/API-key discovery and fail-the-request-on-empty semantics?

## Decorate-then-override auth plane on the vendored provider
**Path/Symbol:** `src/adapter.ts:requestProvider` (`:112-128`, nested `resolve` closure `:119-124`; sole caller `createOpenAICodexAdapter`).
**Signature:** `function requestProvider(provider: Provider, fastMode?: FastModeRegistry): Provider`.
**Data Shape:** Input: the vendored pi-ai Codex provider plus optional Fast Mode registry. Output: a new Provider object that (1) spreads `withOpenAICodexFastMode(provider, fastMode)` FIRST, then (2) overrides the `auth.apiKey` slot with `{ name: 'OpenAI Codex OAuth bearer token', resolve({ credential }) }`. The resolver reads only `credential?.key`: empty/undefined ⇒ `undefined`; otherwise `{ auth: { apiKey }, source: 'OAuth' }`.

### Decisive source
```ts
// src/adapter.ts :112-128
function requestProvider(provider: Provider, fastMode?: FastModeRegistry): Provider {
  return {
    ...withOpenAICodexFastMode(provider, fastMode),
    auth: {
      ...provider.auth,
      apiKey: {
        name: 'OpenAI Codex OAuth bearer token',
        async resolve({ credential }) {
          const apiKey = credential?.key
          return apiKey === undefined || apiKey.length === 0
            ? undefined
            : { auth: { apiKey }, source: 'OAuth' }
        },
      },
    },
  }
}
```

**Flow:** pi-ai's generic adapter asks the provider profile for credentials → the resolver projects the plugin's OAuth credential store value into the apiKey-shaped shape the generic layer already understands → requests carry the subscription access token as a bearer key tagged `source: 'OAuth'`; an empty credential resolves to `undefined`, which fails the request instead of silently degrading to another credential class.
**Invariant:** The resolver NEVER discovers environment variables or persistent api-key credentials — the only input is the explicit override supplied by this plugin; decoration order matters: fast-mode wrapper spread first so the later `auth:` override replaces the auth plane without disturbing payload decoration.
**Probe:** `tests/adapter.spec.ts` (factory-level policy tests exercise this resolver through the assembled adapter; honest caveat: NO dedicated spec targets `auth.apiKey.resolve` directly — evidence is the complete source read plus the passing assembled-adapter suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "^dsh-codex\\.src\\.adapter\\.(requestProvider|createOpenAICodexAdapter|openAICodexModelCatalog)$", limit: 10 });
// observed live: total 3, has_more=false — requestProvider :112-128 (in=1/out=2), createOpenAICodexAdapter :166-190, openAICodexModelCatalog :18-20
```
SOURCE DOC-DRIFT recorded: the "never discovers an API key from the environment" docstring (`:74-79`) is attached to neighbor `isPayloadRecord`, not to its semantic home `requestProvider`; the graph copied the drift faithfully. Source prose drifted; read the code.

## Verdict
Adopt decorate-then-override provider projection with a single-source credential resolver that fails closed on empty. Adapt the credential field names and auth envelope to the host adapter's SPI. Omit ChatGPT-specific header/account plumbing (owned by image-client/search-provider capsules). Coverage caveat: check_index_coverage clean for src/adapter.ts and tests/adapter.spec.ts.
