<!-- capsule-v2 -->
# Pattern route normalization — how do object message patterns become stable routing keys on both client and server?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you turn arbitrary string/number/object message patterns into one canonical, order-independent route string that both the client publisher and the server registry compute identically?

## Shared canonicalizer used by ClientProxy and Server
**Path/Symbol:** `packages/microservices/utils/transform-pattern.utils.ts:transformPatternToRoute` (17-64).
**Signature:** `function transformPatternToRoute(pattern: MsPattern, depth = 0, maxDepth = 5, maxKeys = 20): string`.
**Data Shape:** Input is a pattern scalar or nested plain-object tree; output is the route string. Guards return sentinels `'[MAX_DEPTH_REACHED]'` (depth > 5) and `'[TOO_MANY_KEYS]'` (> 20 keys at one level). Non-string/number/object values are returned **unchanged** (spec pins null, undefined, and Symbol identity).

### Decisive source
```ts
if (isString(pattern) || isNumber(pattern)) {
  return `${pattern}`;
}
if (!isObject(pattern)) {
  // For non-string, non-number, non-object values
  return pattern;
}
if (depth > maxDepth) {
  return '[MAX_DEPTH_REACHED]';
}
const keys = Object.keys(pattern);
if (keys.length > maxKeys) {
  return '[TOO_MANY_KEYS]';
}
const sortedKeys = keys.sort((a, b) => ('' + a).localeCompare(b));
const parts = sortedKeys.map(key => {
  const value = pattern[key];
  let partialRoute = `"${escape(key)}":`;
  if (isString(value)) {
    partialRoute += `"${escape(transformPatternToRoute(value, depth + 1, maxDepth, maxKeys))}"`;
  } else {
    partialRoute += transformPatternToRoute(value, depth + 1, maxDepth, maxKeys);
  }
  return partialRoute;
});
return `{${parts.join(',')}}`;
```

**Flow:** scalar → `${v}`; object → sort keys with localeCompare → emit `"escapedKey":value` per key (string values quoted + escaped, numbers/objects recursed bare) → join as `{...}`. Both sides call the same function (`Server.normalizePattern`, `ClientProxy.normalizePattern`), so agreement is purely syntactic.
**Invariant:** identical patterns in any key order normalize to the same route on both ends; guards bound pathological trees but distinct over-deep/wide patterns can collide into the same sentinel string — accepted by design, never parse routes back for semantics.
**Probe:** `packages/microservices/test/utils/transform-pattern.utils.spec.ts` (order-swapped objects equal `JSON.stringify` form at 1–3 nesting levels; `[null, undefined, Symbol(213)]` returned unchanged; sentinel strings pinned exactly, e.g. depth-6 tree yields `{"a":{"b":{"c":{"d":{"e":{"f":[MAX_DEPTH_REACHED]}}}}}}`).
**Runner caveat:** repo vitest deps not installed this pass — probe expectations quoted from direct spec read, execution blocked.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: ".*transformPatternToRoute.*", limit: 6 });
// live @ pin: rank#1 transformPatternToRoute Function packages/microservices/utils/transform-pattern.utils.ts 17-64
```

## Verdict
Adopt the sorted-key canonical form plus depth/key guards and the unchanged-passthrough rule for non-pattern scalars; adapt `localeCompare` to a deterministic collation if your runtime's locale varies across nodes (both ends must agree); omit Redis buffer-mode specifics when not porting that transport.
