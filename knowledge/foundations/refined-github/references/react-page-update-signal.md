<!-- capsule-v2 -->
# react-page-update-signal — how do observers re-arm when a React SPA re-renders WITHOUT a classic navigation event?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How can a feature's DOM work cancel on EITHER its run signal OR the next framework-driven page update?

## Unified abort signal per update
**Path/Symbol:** `source/github-events/on-react-page-update.tsx:onReactPageUpdate` (:3–14, whole file).
**Signature:** `onReactPageUpdate(callback: (signal: AbortSignal) => void, signal: AbortSignal): void`.
**Data Shape:** callback receives a FRESH composite `AbortSignal` per host update; outer listener lifetime bound to the caller's run signal.

### Decisive source
```ts
document.addEventListener('soft-nav:payload', () => {
	const unifiedSignal = AbortSignal.any([
		signal, // User-provided, likely Turbo page navigation event
		signalFromEvent(document, 'soft-nav:payload'), // A "React page"-specific page navigation event
	]);
	callback(unifiedSignal);
}, {signal});
```

**Flow:** GitHub's React pages re-render without Turbo document events → the adapter listens for the `'soft-nav:payload'` document event → each firing hands the feature a signal that aborts when the FEATURE RUN ends (caller `signal`) or when the NEXT update fires (`signalFromEvent(document, 'soft-nav:payload')`) → observers registered inside the callback self-cancel at whichever comes first.
**Invariant:** (1) every callback invocation gets a NEW unified signal — never reuse the previous one; (2) the outer `addEventListener` itself carries `{signal}` so the whole adapter dies with the feature run (no cross-run leaks); (3) the adapter normalizes React-only updates into the same shape as classic soft navigations so features need one re-arm path.
**Probe:** no direct unit test exists for this file (browser-event-bound; standing helper-tests-only caveat). Executed pins: `grep 'soft-nav:payload|AbortSignal\.any' source/github-events/on-react-page-update.tsx` → lines 7, 8, 10.
**Consumer evidence:** live `trace_path inbound onReactPageUpdate` → single caller `source.features.previous-version.add`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "onReactPageUpdate", direction: "inbound" });
// callers_total: 1 → refined-github.source.features.previous-version: add 1
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt `AbortSignal.any([runSignal, nextUpdateSignal])` per-callback unification for any framework whose route changes don't emit navigation events. Adapt the triggering event name (`soft-nav:payload` is GitHub-specific) and the signal-from-event helper to your host. Coverage caveat: path is `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
