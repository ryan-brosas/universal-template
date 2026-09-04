<!-- capsule-v2 -->
# singleton-init-lifecycle — how do you get React's useEffect cleanup semantics for imperative feature init?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How can a re-invoked init keep exactly its latest instance alive, with or without an AbortSignal?

## Latest-invocation-wins wrapper pair
**Path/Symbol:** `source/helpers/singleton.ts` — `singleton` :9–19, `singletonWithSignal` :27–37 (whole file 37 lines).
**Signature:** `singleton<T extends (...arguments_: any[]) => any>(init: T): T` (init returns optional `() => void` cleanup); `singletonWithSignal(init: (signal: AbortSignal) => void): (signal: AbortSignal) => void`.
**Data Shape:** `singleton`'s wrapped fn returns whatever `init` returns (cleanup captured if function); signal variant closes over one `ReusableAbortController`.

### Decisive source
```ts
return ((...arguments_: Parameters<T>) => {
	if (typeof unmount === 'function') {
		unmount();
	}
	unmount = init(...arguments_);
}) as T;
// singletonWithSignal:
const controller = new ReusableAbortController();
return signal => {
	controller.abortAndReset();
	onAbort(signal, controller);
	init(controller.signal);
};
```

**Flow (cleanup variant):** Nth call → previous cleanup runs FIRST → new init runs; exactly one instance alive at any time ("like React's useEffect" per upstream doc comment). **Flow (signal variant):** Nth call → `abortAndReset()` kills the N−1th async work through the shared controller → `onAbort` links the caller's run signal so a whole-feature abort also cancels the current instance → init receives the fresh controller's signal.
**Invariant:** (1) cleanup must be idempotent-safe because it runs before every re-init; (2) the signal variant's controller is SHARED across invocations — never hand `controller.signal` outside `init`; (3) caller-signal linkage is one-directional (run abort ⇒ instance abort), not vice versa.
**Probe:** no direct unit test exists for this file (standing browser-bound caveat). Executed pins: `grep 'unmount\(\)|abortAndReset|onAbort\(signal, controller\)' source/helpers/singleton.ts` → lines 14, 33, 34.
**Consumer evidence:** live `trace_path inbound singleton` → rgh-feature-descriptions.init + safari/Utilities.swift (the Safari shell mirrors it); graph shows `singletonWithSignal` fan-in 1 within-file pair.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "singleton", direction: "inbound", limit: 40 });
// callers_total: 4 → features.rgh-feature-descriptions.init 1; Utilities(safari) 2
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt both wrappers as the standard shape for imperative UI layers that re-render hosts invalidate (tooltip layers, per-page widgets): latest-wins cleanup without signals, abort-linked reset with them. Adapt the `ReusableAbortController` dependency (abort-utils) to your signal toolkit. Omit nothing — 37 lines, no host coupling. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
