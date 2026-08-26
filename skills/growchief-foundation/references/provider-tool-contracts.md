<!-- capsule-v2 -->
# Provider tool contracts — how do decorator metadata turn provider methods into a portable tool/plugin catalog?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how does `getTools()` know which provider methods are user-selectable steps, their ordering, and their sequencing constraints?

## Reflect.metadata arrays on prototypes + an index-signature abstract class
**Path/Symbol:** decorators `shared/both/utils/tool.decorator.ts:Tool` (:5-16) + `shared/server/plugs/plug.decorator.ts:Plug` (:21-31); catalog readers `bots.service.ts:getTools/getPlugins` (:293-341); base class `shared/server/bots/bots.interface.ts:BotAbstract`.
**Signature:** `Tool(params: ToolParams)` where `ToolParams = { identifier; priority; title; description; weeklyLimit?; allowedBeforeIdentifiers: string[]; notAllowedBeforeIdentifiers: string[]; notAllowedBeforeIdentifier: string[]; appendUrl?; maxChildren? }`; reader: `Reflect.getMetadata('custom:tool', b.constructor.prototype) as Array<{methodName} & ToolParams>`.
**Data Shape:** each application PUSHES `{methodName: propertyKey, ...params}` onto the array stored at metadata key `'custom:tool'` (plugins: `'custom:plugin'`) on the PROTOTYPE — declaration order becomes catalog order.

### Decisive source
```ts
export function Tool(params: ToolParams) {
  return function (target: any, propertyKey: string | symbol) {
    const existingMetadata = Reflect.getMetadata('custom:tool', target) || [];
    existingMetadata.push({ methodName: propertyKey, ...params });
    Reflect.defineMetadata('custom:tool', existingMetadata, target);
  };
}
// stacking two @Tool on ONE method = two catalog entries sharing a body:
@Tool({ priority: 2, identifier: 'linkedin-send-followup-message',
        allowedBeforeIdentifiers: ['linkedin-send-message'], ... })
@Tool({ priority: 3, identifier: 'linkedin-send-message', ... })
async sendMessage(params, lead) {...}
```

**Flow:** providers declare capabilities declaratively → `getTools()` maps botList to `{identifier, label, tools[]}` → frontend renders them as workflow step options and stores the chosen `identifier` in node data → `workflowBotJobs` resolves `tools.find(p.identifier===platform).tools.find(t.identifier===step.data.identifier)` to get `{methodName, priority, appendUrl}` for enqueueing. Sequencing is data-driven: `notAllowedBeforeIdentifiers` are checked against the saved-actions ledger (e.g. connection-request forbids prior connection-request/message), `allowedBeforeIdentifiers` require a prior action (follow-up message requires sent-message).
**Invariant:** plugin variables carry live RegExp objects that CANNOT cross JSON boundaries — `getPlugins()` explicitly serializes them as `{source, flags}` before returning (:330-341), the canonical TS-to-wire regex transport. The index signature on BotAbstract (`[key: string]: ... | ((params, lead) => Promise<...>)`) lets `findProvider[functionName]` dynamic dispatch stay type-checked.
**Probe:** no test runner upstream. Deterministic pins: `grep -n "custom:tool" shared/both/utils/tool.decorator.ts` → :8/:13; stacked decorator block linkedin.provider.ts:352-391; regex serialization bots.service.ts:330-341.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "ToolParams getTools getPlugins", limit: 10 });
```

## Verdict
Adopt: prototype-metadata capability catalogs with priority + before/after sequencing constraints serialized into workflow data. Adapt reflect-metadata to your DI/decorator runtime. Omit the concrete LinkedIn/X tool identifiers.
