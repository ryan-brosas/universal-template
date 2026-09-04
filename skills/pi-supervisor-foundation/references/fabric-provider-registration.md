<!-- capsule-v2 -->
# Fabric provider registration — how does a tool surface get exported both eagerly and on discovery?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What dual registration pattern makes an extension's actions available to a late-loading broker, and how are actions risk-classified?

## registerFabricProvider (`src/fabric-provider.ts`)
**Path/Symbol:** `src/fabric-provider.ts:registerFabricProvider` (:70-115); descriptors :40-68; event names :4-5.
**Signature:** `(pi: ExtensionAPI, controller: {start(outcome, ctx): Promise<string>, getState(): SupervisorState|null}) => void`.
**Data Shape:** Actions: `start` (risk `'agent'`, requires outcome) and `status` (risk `'read'`, no args); schemas are plain JSON Schema with `additionalProperties:false`.

### Decisive source
```ts
const FABRIC_PROVIDER_REGISTER_EVENT = 'pi-fabric:provider:register:v1';
const FABRIC_PROVIDER_DISCOVER_EVENT = 'pi-fabric:provider:discover:v1';
const register = () =>
  pi.events.emit(REGISTER, { version: 1, provider, overwrite: true });   // eager
register();
pi.events.on(DISCOVER, (value) => {                                      // pull-based
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return;
  const event = value as Partial<FabricProviderDiscovery>;
  if (event.version !== 1 || typeof event.register !== 'function') return; // shape-gate
  event.register(provider, { overwrite: true });
});
// invoke:
if (actionName === 'status') return controller.getState();
if (actionName === 'start') return { message: await controller.start(...), state: controller.getState() };
throw new Error(`Unknown supervisor Fabric action: ${actionName}`);
```

**Flow:** registration happens twice by design — once immediately at extension load (push) and again whenever any broker emits the discovery event asking providers to re-register (pull). The start action RETURNS the new state alongside the message so the caller sees post-conditions without a second call. Unknown actions throw rather than return null.
**Invariant:** (1) Discovery payloads are validated by VERSION + callable check before use — foreign/malformed events are silently ignored. (2) `overwrite:true` on BOTH paths means re-registration is idempotent, last-writer-wins. (3) Risk labels are declarative metadata (`agent` mutates supervision state, `read` is pure) for broker-side policy engines. (4) The controller interface keeps THIS module free of SupervisorStateManager imports.
**Probe:** `tests/fabric-provider.test.ts` — single test `registers eagerly and through discovery` (:19-52): asserts eager emit payload `{version:1, overwrite:true}`, `describe('start').risk === 'agent'`, invoke status/start results, and discovery-path re-register.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "registerFabricProvider FABRIC_PROVIDER_DISCOVER_EVENT descriptors", limit: 8 });
```

## Verdict
Adopt push+pull dual registration with versioned shape-gated discovery for any tool-broker integration. Adapt event names and risk taxonomy to your bus. Omit the status action only if you have no read-only surface.
