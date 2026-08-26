<!-- capsule-v2 -->
# Window-cap tracking sentinel — make maxTokens follow contextWindow until the user sets it explicitly

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** Discovery can grow a model's context window after build time — how do you keep an "unset" output cap tracking the window without clobbering an explicit user cap?

## Window-cap tracking sentinel
**Path/Symbol:** `src/models.ts:100-120` (`DEFAULT_MODEL_MAX_TOKENS`, `isWindowTrackedMaxTokens`, `withWindowCappedMaxTokens`); build site `buildKimiModelFromConfig` :122-144; reconcile site `applyKimiOAuthExtrasToModel` :354-406 (capture :359-361, re-cap :403-404).
**Signature:** `isWindowTrackedMaxTokens(model): boolean`; `withWindowCappedMaxTokens<M extends Model<Api>>(model: M): M`.
**Data Shape:** sentinel is value-based, not flag-based: `maxTokens === DEFAULT_MODEL_MAX_TOKENS || maxTokens === model.contextWindow` means "unset / already tracking".

### Decisive source
```ts
// "Explicitly configured" means any value other than the built-in default:
// ensureKimiCodeConfig materializes the full default config (including
// maxTokens) into the home config file, so config-source tracking cannot
// distinguish a deliberate 32000 from a materialized default. A user who
// explicitly sets the default value gets the window cap — indistinguishable
// from the materialized-default case, and the intended new behavior anyway.
const DEFAULT_MODEL_MAX_TOKENS = DEFAULT_KIMI_CODE_CONFIG.model.maxTokens;

function isWindowTrackedMaxTokens(model: Model<Api>): boolean {
  return model.maxTokens === DEFAULT_MODEL_MAX_TOKENS || model.maxTokens === model.contextWindow;
}

function withWindowCappedMaxTokens<M extends Model<Api>>(model: M): M {
  if (!isWindowTrackedMaxTokens(model)) return model;
  return { ...model, maxTokens: model.contextWindow };
}
```
And in the extras applier — capture BEFORE mutation, reconcile AFTER:
```ts
// Capture before extras grow the window: a window-tracked cap must follow
// the new window, an explicit cap must survive unchanged.
const windowTracked = isWindowTrackedMaxTokens(model);
...
if (typeof extras.contextLength === "number" && extras.contextLength > 0) {
  next.contextWindow = extras.contextLength;
}
...
// Reconcile the output cap with the (possibly discovery-updated) window.
if (windowTracked) next.maxTokens = next.contextWindow;
```

**Flow:** at build time `buildKimiModelFromConfig` wraps its literal with
`withWindowCappedMaxTokens`, so a default-or-equal cap immediately becomes
`maxTokens = contextWindow`. When discovery later delivers a bigger `contextLength`,
`applyKimiOAuthExtrasToModel` snapshots the tracked-flag first, grows the window, then
re-caps only if the snapshot said "tracking". Rationale (tests/model-max-tokens.test.ts
header): the host clamps the request cap to `contextWindow − used − 4096`, so
maxTokens = contextWindow yields the server's real output budget instead of truncating
long max-effort reasoning with a fixed small cap.
**Invariant:** explicit caps survive every growth event; the sentinel has one documented
false positive — explicitly configuring exactly the default value (32000) is
indistinguishable from a materialized default because `ensureKimiCodeConfig` writes the
full default tree into fresh config files, defeating source attribution for this one
field. Accepted and documented at models.ts:102-107.

**Probe:** `tests/model-max-tokens.test.ts:16-48` truth table — default ⇒ capped;
discovery growth ⇒ cap follows to 1048576; no-contextLength extras ⇒ stays equal;
explicit 8000 ⇒ preserved at build AND across growth. Runner status: this suite is
BLOCKED live in-lane (`ERR_MODULE_NOT_FOUND '@earendil-works/pi-coding-agent'` from
src/device.ts — host package absent in read-only checkout); anchors verified by direct
read of test + source at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "window capped max tokens tracked context window sentinel", limit: 5 });
// observed: isWindowTrackedMaxTokens #1 (-40.05) tied with withWindowCappedMaxTokens #2 (-40.05)
```

## Verdict
Adopt value-sentinel cap tracking wherever discovery can resize capability windows after
initial construction. Adapt the sentinel pair (default-value OR already-equal) to your
config shape and document the deliberate false positive. Omit only if your host lets you
carry an explicit `capIsExplicit` flag through serialization — this repo shows that route
closed when configs are materialized to disk.
