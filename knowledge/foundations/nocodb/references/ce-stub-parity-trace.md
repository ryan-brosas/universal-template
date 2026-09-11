<!-- capsule-v2 -->
# CE stub parity doctrine — how does the CE build keep EE-only machinery type-safe while shipping inert decorators, and where is the seam?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What must a CE stub preserve so an EE override can replace it without touching call sites?

## Inert-descriptor + no-op-function stub quartet
**Path/Symbol:** `packages/nocodb/src/decorators/trace-command.decorator.ts` (whole 71L: TraceCommand, captureForTrace, getTraceCapture, getTraceCaptureSnapshot, isTraceActive, runUntraced, Untraced) · `command-registry/registry.ts:_OperationRegistryNoop` (whole 29L) · `decorators/nc-cache.decorator.ts:NcCache` (:92–:102 returning bare descriptor).
**Signature:** decorator stubs return `descriptor` untouched; functions return `undefined`/`false`/`{}`; registry exposes register/freeze/resolve/describe/contract as no-ops with resolve/contract → undefined.
**Data Shape:** types stay FULLY declared (`OperationName | OperationNameResolver`, `OperationContract<any>`) — only behavior is stubbed.

### Decisive source
```ts
// CE no-op stub. EE overrides with the real implementation.
export function TraceCommand(_name, _version = 1) {
  return function (_target, _propertyKey, descriptor: PropertyDescriptor) {
    return descriptor;
  };
}
// ...
class _OperationRegistryNoop {
  register<C extends OperationContract<any>>(_c: C, _h: CommandHandler<C>) {}
  resolve(_name: string, _version: number) { return undefined; }
```
(:8–:17, registry :7–:27)

**Flow:** CE services annotate freely (@TraceCommand/@Untraced/@NcCache compile to identity) → OperationName enum lives in CE so annotations don't need EE imports → runUntraced(fn) just calls fn() so system-driven fan-outs work identically in CE → EE swaps implementations via path alias/module override; call sites never change.
**Invariant:** stubs must be SEMANTIC no-ops not throws — `getTraceCapture` returns undefined "outside a trace scope", `isTraceActive()` false, snapshot `{}` — so generic code paths branching on those values behave correctly untraced. The registry variance comment matters for porters typing it: zod schema generics propagate contravariantly, hence `OperationContract<any>` on register. NcCache is a placeholder whose OPTIONS interface is already final — porters should implement against the documented auto-key scheme (`className:functionName:base_id:`).
**Probe:** `cd packages/nocodb && grep -c "CE no-op stub\|CE has no scope\|No-op in CE" src/decorators/trace-command.decorator.ts` (=5 stub markers) and `grep -n "return descriptor;" src/decorators/nc-cache.decorator.ts src/decorators/trace-command.decorator.ts` (nc-cache :100 single; trace-command :18 + :69 = two stubs).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "TraceCommand Untraced runUntraced OperationRegistry NcCache descriptor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the keep-types-drop-behavior stub discipline and single-token swap seams; adapt which surfaces you split CE/EE; omit entirely in single-edition ports (call sites inline). Companion: widget-handler-contract.md mines the same doctrine for widget factories — this capsule owns the trace/cache family. Coverage caveat: by construction there is nothing to behavior-test in CE; probes pin stub shape.
