<!-- capsule-v2 -->
# Composite plugin assembly order — in what order and under which service gates does a provider bundle register all its surfaces so conflicts fail before side effects and nothing freezes request-time state?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should one `apply(ctx, config)` wire a credential store, policy, adapter, search provider, routes, and tools so a duplicate-provider conflict aborts registration cleanly and optional services are awaited only where needed?

## apply — the wiring-order kernel
**Path/Symbol:** `src/index.ts:164-212 apply` (with the double-defaulting `Config` schema at :146-156).
**Signature:** `export function apply(ctx: Context, config: Config): void`.
**Data Shape:** constructs one `OpenAICodexService` (credentials + live policy), one `FastModeRegistry`; registers the LLM adapter, one search provider, auth/settings routes, imagegen tool, and read-image enhancement; provides everything through the `'openAICodex'` context slot.

### Decisive source
```ts
installOpenAICodexSearchEvent()
const service = new OpenAICodexService({ /* config defaults */ modelCatalog: openAICodexModelCatalog() })
const fastMode = new FastModeRegistry()
assertNoOpenAICodexProviderConflict(ctx.llm.listProviders().map(provider => provider.id))
ctx.provide('openAICodex', service)
ctx.inject(['settings'], settingsCtx => { service.attachSettings(settingsCtx) })
ctx.llm.registerAdapter([OPENAI_CODEX_PROVIDER], createOpenAICodexAdapter(
  credentials,
  () => ctx.get('attachments'),
  () => imageTools.responseApiSnapshot(),
  fastMode,
  () => imageTools.modelCatalogSnapshot().models,
))
```

**Flow:** install the session-event vocabulary FIRST (so later search dispatch can always record) → build the service → fire the conflict assert BEFORE any registry mutation → provide the shared slot → then an ascending inject ladder, each rung demanding only the services that surface needs: `['settings']` for preference attachment, `['webServer']` for auth routes, `['tools','fs','attachments']` for imagegen, `['tools','fs','attachments','agents']` for read-image enhancement.
**Invariant:** the conflict assert observes only pre-existing provider ids and throws before `provide`/`registerAdapter`, so a failed load leaves no partial registration; dependencies captured as zero-argument closures (`() => ctx.get('attachments')`, snapshot getters) are re-evaluated per request, never frozen at apply time; the search provider's `resolveRequestId` uses optional chaining with a `randomUUID()` fallback so a missing agents service degrades instead of throwing during registration.
**Probe:** `tests/loader-composition.spec.ts:24-73` — loads the REAL module map through a Cordis Loader + include plugin from a temp cordis.yml (`models: [gpt-5.6-luna, gpt-5.6-terra]`), asserts `ctx.llm.listProviders()` equals exactly `[{ id: 'openai-codex', name: 'OpenAI Codex' }]`, `listModels` returns those two ids in order, then `entry.fiber.dispose()` makes `listProviders()` empty again.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "dsh-codex\\.src\\.apply", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt conflict-assert-before-register, provide-one-shared-slot composition, ascending per-surface inject ladders, and closure-based late binding of request-time state. Adapt the Cordis-specific `provide`/`inject`/effect vocabulary and the config schema defaults. Omit eager `ctx.get` of optional services at apply time — that is exactly the failure mode this ordering avoids. Coverage: src/index.ts no_recorded_issue + metadata_match; probe suite is a full real-Loader integration, not mocks. Cross-references: doctor-diagnostics (the conflict assert itself), service-facade (the provided slot).
