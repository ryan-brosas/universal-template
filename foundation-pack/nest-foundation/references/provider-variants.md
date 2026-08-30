<!-- capsule-v2 -->
# Provider variant normalization — how do class/value/factory/existing providers collapse into one runtime wrapper shape?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What per-variant fields must be set so the injector treats every provider uniformly?

## Module.addCustomProvider family + InstanceWrapper.mergeWith
**Path/Symbol:** `packages/core/injector/module.ts:addCustomProvider` (312-331) with `addCustomClass` (356-386), `addCustomValue` (388-410), `addCustomFactory` (412-440), `addCustomUseExisting` (442-462); `instance-wrapper.ts:mergeWith` (497-516).
**Signature:** `addCustomProvider(provider, collection, enhancerSubtype?): InjectionToken` (returns `provider.provide`).
**Data Shape:** discriminated by key: `useClass` / `useValue` / `useFactory` / `useExisting`; token = `provide` (Type | string | symbol).

### Decisive source
```ts
// useValue → instance is READY at registration time
instance: instanceDecorator ? instanceDecorator(value) : value,
isResolved: true,
async: value instanceof Promise,          // injector awaits it during resolveComponentHost

// useFactory → metatype IS the factory fn; deps come from inject
metatype: factory as any,
inject: inject || [],

// useExisting → ALIAS: one dep on the target token, resolved instance shared
inject: [useExisting],
isAlias: true,

// scope/durable default from the CLASS when not given on the provider record
if (isUndefined(scope))   scope   = getClassScope(useClass);
if (isUndefined(durable)) durable = isDurable(useClass);
```

**Flow:** classify by presence of provide/use* keys → build InstanceWrapper with variant-appropriate fields → later `replace()`/`overrideProvider` mutates an existing wrapper in place via mergeWith (value ⇒ clears metatype+inject and pins DEFAULT scope with a resolved instance; factory ⇒ swaps metatype+inject).
**Invariant:** Only value providers are born resolved (`isResolved:true`); async values are flagged not awaited. Aliases never get their own constructor run — lifecycle iteration filters them via `getNonAliasProviders`. Scope inheritance flows provider-record → underlying class.
**Probe:** `packages/core/test/injector/module.spec.ts` (custom-provider variants) + `packages/core/test/injector/helpers/provider-classifier.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "addCustomProvider addCustomUseExisting mergeWith isAlias", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-wrapper normalization with variant flags (async/isAlias/inject); adapt override semantics if you support hot replacement; omit the instanceDecorator instrumentation hook. Porting wrong: treating aliases as normal providers double-instantiates targets and fires their hooks twice.
