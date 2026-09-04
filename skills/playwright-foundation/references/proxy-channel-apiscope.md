<!-- capsule-v2 -->
# Proxy channel + apiZone report-once — why is every channel a Proxy, and when does an API call get reported?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** How can one client object expose every protocol method with validation, tracing, and timeout plumbing — without hand-writing each method or double-reporting nested calls?

## Channel as Proxy; first non-internal call in a zone reports
**Path/Symbol:** `packages/playwright-core/src/client/channelOwner.ts:ChannelOwner._createChannel` (157-187) + `_wrapApiCall` (189-224).
**Signature:** channel getter: `(params, options: { signal?: AbortSignal, timeout?: number } = {}) => Promise<Result>` per protocol method; `_wrapApiCall<R>(func: (apiZone: ApiZone) => Promise<R>, options?: { internal?: boolean, title?: string }): Promise<R>`.
**Data Shape:** ApiZone `{ apiName, frames: StackFrame[], title?, internal?, reported, userData, stepId?, error? }`; metainfo lookup `getMetainfo({ type, method })` decides whether the method is internal.

### Decisive source
```ts
return async (params: any, options: { signal?: AbortSignal, timeout?: number } = {}) => {
  return await this._wrapApiCall(async apiZone => {
    const validatedParams = validator(params, '', this._validatorToWireContext());
    const { signal, timeout = 0 } = options;
    if (!apiZone.internal && !apiZone.reported) {
      // Reporting/tracing/logging this api call for the first time.
      apiZone.reported = true;
      this._instrumentation.onApiCallBegin(apiZone, { type: this._type, method: prop, params });
      ...
      return await this._connection.sendMessageToServer(this, prop, validatedParams, { ...apiZone, signal, timeout });
    }
    // Since this api call is either internal, or has already been reported/traced once,
    // passing as internal.
    return await this._connection.sendMessageToServer(this, prop, validatedParams, { internal: true, signal, timeout });
  }, { internal });
};
```

**Flow:** Proxy `get` consults the generated Params validator for the property name; if found it returns an async function that (1) wraps in `_wrapApiCall`, which reuses the *existing* zone if one is on the stack (`existingApiZone` → run inner func directly), else creates a fresh zone with a captured library stack trace and derived apiName; (2) validates params to wire form; (3) reports exactly once — the outermost user-visible call fires `onApiCallBegin`, everything nested/re-entrant goes `internal: true`; (4) on failure, `_wrapApiCall` prefixes the error message with the apiName and rebuilds the stack from library frames (`apiName.startsWith('_')` falls back to the explicit title).
**Invariant:** Exactly one instrumentation begin/end pair per user-facing API call, no matter how many protocol messages implement it; internal calls never create zones of their own (they join the caller's), so traces show user intent, not implementation steps. The channel proxy must expose `_object` for guid marshalling back over the wire (`tChannelImplToWire` checks `arg._object instanceof ChannelOwner`).
**Probe:** `grep -c "apiZone.reported = true" packages/playwright-core/src/client/channelOwner.ts` → `1`; `grep -c "existingApiZone" packages/playwright-core/src/client/channelOwner.ts` → `3`; `grep -c "expected channel" packages/playwright-core/src/client/channelOwner.ts` → `1`; `grep -c "apiName.startsWith('_')" packages/playwright-core/src/client/channelOwner.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "_wrapApiCall", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: returns `client.channelOwner.ChannelOwner._wrapApiMethod ... channelOwner.ts 189-224`.)

## Verdict
Adopt the Proxy-over-validator surface, the reuse-or-create zone rule, and report-once semantics for tracing/logging. Adapt the generated validator layer (Playwright's is codegen'd from the protocol) and the apiName derivation to your host's naming. Omit jest-friendly `toJSON()` unless embedding in test runners. Behavior pinned end-to-end by `tests/library/browsercontext-events.spec.ts` ("console event should work @smoke", line 20) which drives a full wrap→send→dispatch cycle; the report-once split itself is observable via trace output, not asserted by unit test — keep the grep pins as contract evidence at this commit.
