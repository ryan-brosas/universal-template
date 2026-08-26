<!-- capsule-v2 -->
# ContextUtils — how are sparse route-argument arrays sized, merged, and filled?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does the router know how long the handler's arguments array must be when decorators sit at arbitrary parameter indexes — and why `undefined` fills instead of holes?

## getArgumentsLength / createNullArray / mergeParamsMetatypes / mapParamType / reflectCallbackMetadata
**Path/Symbol:** `packages/core/helpers/context-utils.ts:getArgumentsLength` (:50-54), `createNullArray` (:56-60), `mergeParamsMetatypes` (:62-73), `mapParamType` (:22-25), `reflectCallbackParamtypes` (:27-32), `reflectCallbackMetadata` (:34-40).
**Signature:** `getArgumentsLength(keys: string[], metadata): number`; `createNullArray(length): any[]` (fills with `undefined`); `mergeParamsMetatypes(paramsProperties, paramtypes)`.
**Data Shape:** ROUTE_ARGS_METADATA keys are `"index:type:data"` composite strings; values are `ParamProperties { index, type, data, pipes, extractValue, schema? }`.

### Decisive source
```ts
public getArgumentsLength<T>(keys: string[], metadata: T): number {
  return keys.length ? Math.max(...keys.map(key => metadata[key].index)) + 1 : 0;
}
public createNullArray(length: number): any[] {
  const a = new Array(length);
  for (let i = 0; i < length; ++i) a[i] = undefined;   // densify — NO array holes
  return a;
}
public mergeParamsMetatypes(paramsProperties, paramtypes) {
  if (!paramtypes) return paramsProperties;             // design:paramtypes absent ⇒ passthrough
  return paramsProperties.map(param => ({ ...param, metatype: paramtypes[param.index] }));
}
```

**Flow:** enumerate decorated params → args length = MAX(index)+1 (not count of decorated params!) → allocate dense undefined array → per-param: extract raw value via RouteParamsFactory, run pipes chain, place at its index → metatypes merged by INDEX from PARAMTYPES_METADATA for ValidationPipe's skip gate.
**Invariant:** (1) MAX+1 sizing is what makes `handler(@Query('a') a)` still receive `[value, undefined]` when the method signature has more params than decorators — positional JS calls can't skip slots. (2) The explicit undefined fill exists because SPARSE arrays (`new Array(n)`) iterate differently (`for..of` yields nothing for holes) and the pass-1 dense-metadata fastpath probes holes to detect request-scoped factories. (3) `mapParamType` splits the composite key on ':' taking segment 0 — data containing ':' is preserved downstream because only the first split matters.
**Probe:** `packages/core/test/helpers/context-utils.spec.ts` — "should return maximum index + 1" :71, createNullArray :85, mergeParamsMetatypes passthrough :95, getCustomFactory curried-null identity :117.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ContextUtils getArgumentsLength createNullArray mergeParamsMetatypes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt max-index sizing + dense-fill argument assembly for any decorator-driven invocation protocol; adapt the metadata key grammar; omit metatype merging if your validator doesn't need design types. Porting wrong: using `params.length` as the size (drops trailing undeclared params), or leaving array holes (breaks hole-probing fast paths and iteration).
