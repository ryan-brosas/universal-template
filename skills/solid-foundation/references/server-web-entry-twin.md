<!-- capsule-v2 -->
# Server web-entry twin — what must a solid-js/web server entry provide beyond dom-expressions, and what does it deliberately compile Portal down to?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (gen 2026-08-25T20:12:15Z). **Question:** Which pieces of solid-js/web are re-exports, which are local implementations, and why is there a mergeProps override?

## web/server/index.ts entry surface
**Path/Symbol:** `packages/solid/web/server/index.ts:createDynamic` (:22-35), `Dynamic` (:43-46), `Portal` (:48-50), re-export/override block (:4-20); `packages/solid/web/server/server.ts:1`.
**Signature:** `function createDynamic<T extends ValidComponent>(component: () => T | undefined, props: ComponentProps<T>): JSX.Element`; `function Portal(props: { mount?: Node; useShadow?: boolean; children: JSX.Element })`.
**Data Shape:** NO index coverage caveat needed (no_recorded_issue); `./server.ts` is a single line `export * from "dom-expressions/src/server"` — the external boundary this entry decorates.

### Decisive source
```ts
export function createDynamic<T extends ValidComponent>(
  component: () => T | undefined,
  props: ComponentProps<T>
): JSX.Element {
  const comp = component(),
    t = typeof comp;

  if (comp) {
    if (t === "function") return (comp as Function)(props);
    else if (t === "string") {
      return ssrElement(comp as string, props, undefined, true);
    }
  }
}
...
export function Portal(props: { mount?: Node; useShadow?: boolean; children: JSX.Element }) {
  return "";
}
```

**Flow:** The client's Dynamic lives in dom-expressions; the SERVER twin cannot inherit it, so index.ts implements it locally: truthy component → function components are INVOKED directly with props, string tags route to `ssrElement(tag, props, undefined, true)` (children slot passed as undefined; literal `true` in the svg flag position), anything else renders `undefined`. `Dynamic` is a thin wrapper that splitProps-strips `component` and defers through an accessor (`() => props.component`) so reactivity survives. `Portal` compiles to `""` — mount/useShadow are accepted for signature parity and discarded. Above the locals, the entry re-exports control flow (For/Show/Suspense/SuspenseList/Switch/Match/Index/ErrorBoundary) from solid-js (whose server twins replace them) and explicitly OVERRIDES `mergeProps` from dom-expressions' server module with solid-js's own (:15-16 comment). `isServer = true`, `isDev = false` as literal constants.
**Invariant:** Signature parity with the browser entry is preserved even where behavior collapses to nothing (Portal → ""), so user code type-checks and runs unmodified on both targets. The ssrElement import resolves to dom-expressions via `./server.js` — note the graph's outbound trace links createDynamic to `web/src/server-mock.ssrElement` by NAME only; that is the browser stub twin, not this import (same-name resolution caveat).
**Probe:** No dedicated spec file covers web/server/index.ts at this pin (honest test caveat — claims cite source lines only). Adjacent pin: `web/test/server-mock.spec.tsx` pins the stub family's console.error/undefined contract. Byte anchor: line 49 `return "";`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "server web render hydration code generation", limit: 10 });
```

## Verdict
Adopt the three-part entry shape: external core (dom-expressions re-export) + local implementations only for what the core lacks (Dynamic/Portal) + deliberate override points (mergeProps). Adapt the override list to whatever your DOM layer also ships. Omit Portal's mount semantics entirely on the server — "" is the contract.
