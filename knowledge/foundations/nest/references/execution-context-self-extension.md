<!-- capsule-v2 -->
# ExecutionContextHost — one args-triple, three transport views via Object.assign self-extension

**Source:** nest MIT `master@canonical pin 61b03510`; Codebase Memory `nest`. **Question:** How do guards/interceptors/filters see the SAME request through different transport APIs, and what does switchToHttp actually do?

## ExecutionContextHost
**Path/Symbol:** `packages/core/helpers/execution-context-host.ts:switchToHttp` (:49-55), `switchToRpc` (:42-47), `switchToWs` (:57-63), `setType/getType` (:18-24).
**Signature:** `constructor(args: any[], constructorRef: Type | null = null, handler: Function | null = null)`; `switchToHttp(): HttpArgumentsHost`.
**Data Shape:** private `args` array (HTTP convention `[req, res, next]`), contextType string defaulting to `'http'`.

### Decisive source
```ts
switchToHttp(): HttpArgumentsHost {
  return Object.assign(this, {
    getRequest: () => this.getArgByIndex(0),
    getResponse: () => this.getArgByIndex(1),
    getNext: () => this.getArgByIndex(2),
  });
}
```

**Flow:** every consumer (guards, interceptors, pipes-adjacent code, exception filters) receives the SAME host instance built over `[req, res, next]` → calling a `switchTo*()` method grafts that transport's accessor closures ONTO the host itself and returns it → repeated switches just overwrite the grafted methods; arg positions stay authoritative.
**Invariant:** Positional contract is absolute: HTTP = req/res/next at 0/1/2, RPC = data/context at 0/1, WS = client/data at 0/len−1. Because accessors close over `getArgByIndex`, mutating the args array (e.g. pipes filling slots) is immediately visible to any previously-obtained view. The class is a stateful adapter, not a wrapper — there is no separate per-transport object.
**Probe:** `packages/core/test/helpers/execution-context-host.spec.ts` ("should return constructorRef", "should return args", type/accessor assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ExecutionContextHost switchToHttp switchToRpc", limit: 5 });
```

## Verdict
Adopt the single-host-self-extension trick when you want one context object across transports; adapt arg positions to your convention; omit WS/RPC views if single-transport. Porting wrong: returning NEW objects per switchTo call breaks identity checks (`ctx === ctx.switchToHttp()`) some userland relies on.
