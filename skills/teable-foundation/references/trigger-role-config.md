<!-- capsule-v2 -->
# Trigger role config contract — which env vars split producer/consumer duties for the computed outbox?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the full env surface and its validation semantics?

## computedOutboxTriggerConfig
**Path/Symbol:** `apps/nestjs-backend/src/configs/computed-outbox-trigger.config.ts:computedOutboxTriggerConfig` (:19–43; helpers :6–17).
**Signature:** `registerAs('computedOutboxTrigger', () => ({...}))` consumed via `ComputedOutboxTriggerConfig()` DI decorator.

### Decisive source
```ts
export const readComputedOutboxBoolean = (value, fallback) => {
  if (value == null) return fallback;
  return ['1','true','yes','on'].includes(value.trim().toLowerCase());      // :11
};
const readPositiveInteger = (value, fallback) => {                          // :14–17
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
};
```

**Flow:** six knobs — producer/consumer enabled (boolean-truthy list, default true both), trigger concurrency (8), publish timeout ms (1000), monitor concurrency (4), monitor interval ms (30000); positive-int validator silently falls back on garbage (0/negative/non-integer ⇒ default) unlike processors that throw.
**Invariant:** Defaults keep BOTH roles on — single-node deployments work with zero env; splitting roles is purely a scale-out concern. Silent-fallback integer parsing means a typo'd value degrades to default rather than crashing boot.
**Probe:** `apps/nestjs-backend/src/configs/computed-outbox-trigger.config.spec.ts` (validator matrix incl. boolean truthy variants).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "computedOutboxTriggerConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt truthy-list booleans + silent-positive-int fallback; adapt names to your config namespace; omit Nest registerAs wrapper.
