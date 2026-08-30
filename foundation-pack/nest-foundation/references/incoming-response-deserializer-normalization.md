<!-- capsule-v2 -->
# IncomingResponseDeserializer normalization — what should a client do when a reply is a bare foreign value with no correlation envelope?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How does the client side of a transport normalize arbitrary response payloads into the `{id, err, response, isDisposed}` shape its correlation slots expect?

## Mirror-image ladder; foreign values are terminal by definition
**Path/Symbol:** `packages/microservices/deserializers/incoming-response.deserializer.ts:IncomingResponseDeserializer` (7-36; `deserialize` 8-13, `isExternal` 15-27, `mapToSchema` 29-35); role-based default install `packages/microservices/client/client-proxy.ts:ClientProxy.initializeDeserializer` (220-231).
**Signature:** `deserialize(value: any, options?: Record<string, any>): IncomingResponse | Promise<IncomingResponse>`.
**Data Shape:** input = raw reply payload (any shape); output = `{id, response, err?, isDisposed}` — the exact record shape consumed by `ClientProxy.createObserver`'s three-arm ladder (`response!==undefined && isDisposed` → next+complete; bare `isDisposed` → complete only).

### Decisive source
```ts
deserialize(value, options?) {
  return this.isExternal(value) ? this.mapToSchema(value) : value;
}
isExternal(value) {
  if (!value) return true;
  if (!isUndefined(value.err) || !isUndefined(value.response) ||
      !isUndefined(value.isDisposed)) return false;
  return true;
}
mapToSchema(value) {
  return {
    id: value && value.id,
    response: value,
    isDisposed: true,          // foreign value ⇒ terminal BY DEFINITION
  };
}
```

**Flow:** the server→client mirror of `incoming-request-deserializer-channel-fallback.md`: truthy objects exposing any of `err` / `response` / `isDisposed` pass through untouched (spec pins `.toBe` for both success and error envelopes); anything else becomes `{id: maybe-undefined, response: <itself>, isDisposed: true}`. Wrapping as terminal is the safe default — a bare value cannot carry a dispose flag, so treating it as one-more-frame-of-a-stream would hang the waiter forever. Note the asymmetry vs the request side: no options/channel involvement, and `id` is salvaged opportunistically from the payload.
**Invariant:** a deserializer may NEVER emit an object that satisfies none of the observer arms' expectations — every output must be either the original envelope or a TERMINAL synthetic envelope; presence tests stay on `!isUndefined`, not truthiness (an explicit `err: null` still counts as internal).
**Probe:** `packages/microservices/test/deserializers/incoming-response.deserializer.spec.ts` (`{id,response:{}}` and `{id,err:{}}` both returned by identity; external `{id:'1', array:[1,2,3]}` → `{id:'1', isDisposed:true, response:<same object>}`).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "incoming response deserializer isExternal mapToSchema", limit: 10 });
// live @ pin: rank#2/#4/#5 IncomingResponseDeserializer.isExternal(15-27)/deserialize(8-13)/mapToSchema(29-35)
await mcp.codebase_memory.get_code_snippet({ project: "nest", qualified_name: "nest.packages.microservices.client.client-proxy.ClientProxy.createObserver" });
// live @ pin: consumer of this shape — response!==undefined && isDisposed ⇒ next+complete; bare isDisposed ⇒ complete only
```

## Verdict
Adopt the terminal-by-default normalization for any client correlating replies over a schema-less channel; adopt the three-key presence test so error envelopes with nullish fields still route internally. Adapt the opportunistic `id` salvage to wherever your correlation id lives. Omit nothing lightly — dropping the `isDisposed: true` default reintroduces the hung-waiter class of bug this capsule exists to prevent.
