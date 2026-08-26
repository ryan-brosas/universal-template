<!-- capsule-v2 -->
# Fast-mode injection — inject a provider payload field only when a toggle is active for a supported model

**Source:** pi-better-openai (MIT, `main@86814e9047996abba08e4c907e23286329196fe0`); Codebase Memory `pi-better-openai`. **Question:** How does an extension conditionally add a field (e.g. `service_tier: "priority"`) to an outgoing provider request payload only while a toggle is active and the current model is allow-listed — without mutating the caller's payload object?

## Fast-mode provider injection
**Path/Symbol:** `src/fast-controller.ts:FastController` (37–112); `injectProviderPayload` (89–100), `applyDesiredState` (49–51), `initializeForSession` (53–57), `setDesired` (59–62); helpers `currentModelKey` (5–7), `supportsFast` (9–15), `modelList` (17–21), `fastStateText` (23–35).
**Signature:** `class FastController { desiredActive: boolean; active: boolean; constructor(serviceTier: string); applyDesiredState(ctx, cfg): void; setDesired(ctx, cfg, next): void; injectProviderPayload(event: { payload?: unknown }, ctx, cfg): unknown }`.
**Data Shape:** `active` (actually injecting) is derived from `desiredActive && supportsFast(ctx, cfg.supportedModels)`; `supportsFast` matches the current `ctx.model` provider+id against the configured `SupportedModel[]`. `injectProviderPayload` returns `undefined` when inactive or the payload is not a record, else a new object `{ ...event.payload, service_tier: this.serviceTier }`.

### Decisive source
```ts
// supportsFast: exact provider+id match against the allow-list
return supportedModels.some((model) =>
  model.provider === current.provider && model.id === current.id);

// applyDesiredState: active is derived, not stored independently
this.active = this.desiredActive && supportsFast(ctx, cfg.supportedModels);

// injectProviderPayload: non-mutating spread; returns undefined when inactive
if (!this.active || !supportsFast(ctx, cfg.supportedModels) || !isRecord(event.payload))
  return undefined;
this.lastInjectedAt = Date.now();
return { ...event.payload, service_tier: this.serviceTier };
```

**Flow:** (1) `initializeForSession` seeds `desiredActive` from persisted config (or the CLI flag), then `applyDesiredState` derives `active`; (2) `setDesired` toggles `desiredActive` and re-derives `active`; (3) on each provider request, `injectProviderPayload` returns the payload with `service_tier` only when `active` and the model is supported; (4) `debugLines`/`stateText` report desired vs active vs last-injected for diagnostics.

**Invariant:** the original `event.payload` object is never mutated (a new object is returned); injection happens only when `active` AND the current model is in the allow-list; `active` is always derived from `desiredActive && supportsFast` so it cannot drift out of sync on model switch.

**Probe:** `tests/fast.test.ts` — `injects priority service tier when persisted fast mode is active for a supported model` (result `{ model:"gpt-5.5", messages:[], service_tier:"priority" }` and the original `payload` is unchanged); `does not inject for unsupported models and leaves the payload unchanged` (gpt-4.1 → undefined, payload untouched); `does not inject when fast mode is disabled`; `model selection deactivates injection for unsupported models and reactivates for supported models`. Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test file, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "FastController injectProviderPayload supportsFast applyDesiredState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the desired-vs-active split, the derived `active = desiredActive && supportsFast` invariant, and the non-mutating `{ ...payload, service_tier }` spread. Adapt the service-tier value, the allow-list source, and the provider event hook to the host. Omit the pi `ExtensionContext`/flag wiring and the settings summary UI unless a target needs them.
