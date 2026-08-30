<!-- capsule-v2 -->
# Child model & context inheritance — subprocess LLM calls inherit the session's cwd + active provider/model, and trusted extension SOURCES pass through Pi's own resolver

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** A background child `pi -p` call used to run with the override-or-default model in an arbitrary cwd — how does it inherit what the interactive session actually uses, without weakening the sanitized-extension admission list?

## resolveChildPiModel / buildChildPiPromptArgs / childExtensionSources
**Path/Symbol:** `src/handlers/pi-child-process.ts` — `resolveChildPiModel` (:24–32), options gain `cwd?`/`model?: ChildPiModel` (:34–39), `childExtensionSources` (:229–251), `appendOwnExtensionArgs` (:253–262), `buildChildPiPromptArgs(prompt, config, _argv, activeModel?)` (:264–287), `basePromptArgs` (:289+). Callers: background-review :111–119 (`cwd: ctx.cwd, model: resolveChildPiModel(ctx.model), signal: ctx.signal`, timeout 120000), correction-detector :214–222, session-flush :117–123.
**Signature:** `resolveChildPiModel(model?: {provider?, id?}) → {provider, id} | undefined`; model arg resolution = `normalizedModelOverride(config) ?? "${activeModel.provider}/${activeModel.id}"`.
**Data Shape:** exec opts now carry `{ cwd, timeout }` alongside the prompt file/cancel-sentinel machinery (mock asserts `execCalls[0][2]` deep-equals `{ cwd: "/tmp/local-session", timeout: 125000 }` — 120s budget + 5s watchdog margin).

### Decisive source
```ts
export function resolveChildPiModel(model) {
  return model?.provider && model.id ? { provider: model.provider, id: model.id } : undefined;
}

// buildChildPiPromptArgs — configured override WINS; active session model is the fallback:
const model = normalizedModelOverride(config)
  ?? (activeModel?.provider && activeModel.id ? `${activeModel.provider}/${activeModel.id}` : undefined);

// appendOwnExtensionArgs / childExtensionSources:
args.push("--no-extensions");
for (const extensionSource of childExtensionSources(config)) args.push("-e", extensionSource);
// configured childExtensionPaths pass through UNRESOLVED so Pi's -e resolver owns
// path expansion + package-source handling exactly as for normal CLI invocations;
// only auto-DETECTED adapter paths keep the local existsSync check.
```

**Flow:** handler event → `resolveChildPiModel(ctx.model)` snapshots provider/id → spawn inherits `ctx.cwd` (so relative paths and project-local config behave as the user expects) and `ctx.signal` (cancellation propagates to the watchdog sentinel) → args place `--model provider/id` only when something resolved → retry-without-overrides path (`basePromptArgs`) also carries the active model.
**Invariant:** precedence stays override > inherited-active-model > Pi default; a partially-specified model (provider without id) resolves to UNDEFINED rather than guessing. The trust boundary moves but does not widen: previously ALL `-e` candidates were normalize+existsSync'd locally; now CONFIGURED sources are forwarded verbatim to Pi's resolver (they were explicitly trusted by config), while DISCOVERED sources (auth-adapter scan) still get the existence check before forwarding. `--no-extensions` remains unconditional.
**Probe:** `npx tsx --test tests/handlers/pi-child-process.test.ts` — "inherits the active provider/model when no override is configured" (:282), "prefers the configured model override over the active session model" (:289), "passes configured extension sources through Pi's -e resolver and excludes inherited extensions" (:316). `npx tsx --test tests/handlers/background-review.test.ts` — "inherits the active session model and execution context for subprocess fallback" (:774, asserts both the `--model local-llama/local-9b` arg position AND `{cwd, timeout}` exec opts). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "resolveChildPiModel buildChildPiPromptArgs childExtensionSources", limit: 5 })`

## Verdict
Adopt explicit context inheritance for headless child agents plus resolver-delegated extension sourcing. Adapt flag names (`-e`, `--no-extensions`) to your CLI. Pair with `child-subprocess-transport.md` (spawn/watchdog/retry mechanics unchanged) and `auth-adapter-discovery.md` (the discovered-source feed).
