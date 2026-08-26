<!-- capsule-v2 -->
# Server-handoff gating — why do interactive features disable during SSR/hydration and how is "hydration in progress" detected in React 18?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the env handoff protocol and the useIsHydratingInReact18 trick?

## env / useServerHandoffComplete
**Path/Symbol:** `packages/@headlessui-react/src/utils/env.ts:1-52` (Env class); `packages/@headlessui-react/src/hooks/use-server-handoff-complete.ts:13-60`.
**Signature:** `env: Env { current: 'client'|'server'; handoffState: 'pending'|'complete'; nextId(); set(); reset(); get isServer/isClient/isHandoffComplete }`; `useServerHandoffComplete(): boolean`.
**Data Shape:** module-singleton; consumers: Portal target creation, FocusTrap features (zeroed while !complete), Dialog enabled flag, useId mock pairing.

### Decisive source
```ts
// React-18 hydration detection WITHOUT version sniffing:
function useIsHydratingInReact18(): boolean {
  let isServer = typeof document === 'undefined'
  if (!('useSyncExternalStore' in React)) return false          // React < 18: can't know
  const useSyncExternalStore = ((r) => r.useSyncExternalStore)(React) // bundler-safe access
  return useSyncExternalStore(() => () => {},
    () => false,                       // client snapshot: NOT hydrating after mount
    () => (isServer ? false : true))   // server snapshot: TRUE => hydration pass sees it
}
export function useServerHandoffComplete() {
  let isHydrating = useIsHydratingInReact18()
  let [complete, setComplete] = React.useState(env.isHandoffComplete)
  if (complete && env.isHandoffComplete === false) setComplete(false)  // test-env reset (rules-of-hooks exception, deliberate)
  React.useEffect(() => { if (complete === true) return; setComplete(true) }, [complete])
  React.useEffect(() => env.handoff(), [])      // flip singleton pending->complete once mounted
  if (isHydrating) return false                 // suppress DOM-touching features during hydration
  return complete
}
```

**Flow:** server render → env.isServer, complete=false → Portal renders null, FocusTrapFeatures.None, Dialog enabled=false → hydration pass → getServerSnapshot returns true ⇒ isHydrating ⇒ still false → post-mount effects flip env.handoff + setState → re-render with complete=true enables portals/focus/scroll-lock.
**Invariant:** features that CREATE or MOVE DOM must stay off until hydration finishes to avoid hydration mismatches; the getServerSnapshot=true trick makes ONLY the hydration render see "hydrating" (later client renders use the client snapshot=false); test-env reset exists because jsdom reuses the module registry across tests.
**Probe:** deterministic checks executed: bundler-safe accessor pattern; snapshot truth table. Direct tests: `src/test-utils/ssr.tsx` renderToString harness exercises SSR paths across component suites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useServerHandoffComplete", name_pattern: "^useServerHandoffComplete$", limit: 5 });
```

## Verdict
Adopt the three-phase gate (server → hydrating → complete) verbatim for any DOM-mutating headless primitive; adapt the React-18 probe if your minimum React already requires useSyncExternalStore; omit the legacy env.set/reset machinery unless you support streaming swap. This is the answer to "why does my portaled dialog flash on hydration" — it shouldn't, by design.
