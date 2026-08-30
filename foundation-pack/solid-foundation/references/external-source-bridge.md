<!-- capsule-v2 -->
# Solid external-source bridge — how do third-party observables plug into tracking with a composable factory chain and transition-safe re-subscription?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 provenance refresh: originally authored against the retired `ext-solid` graph at the identical pin; retrieval re-executed on `solid` 2026-08-25, gen 2026-08-25T20:12:15Z). **Question:** How does enableExternalSource wrap computation functions, and what fixes the lost-updates-after-transition bug?

## createComputation's fn wrapper + triggerInTransition re-trigger
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:enableExternalSource` (:1276-1299) and the wrapper block inside `createComputation` (:1484-1516).
**Signature:** `enableExternalSource(factory: ExternalSourceFactory, untrack?: <V>(fn: () => V) => V)`; `ExternalSourceFactory = (fn: EffectFunction, trigger: () => void) => { track(x), dispose() }`.
**Data Shape:** module `ExternalSourceConfig` singleton; per-computation closure state `ordinary`, `inTransition?: ExternalSource`, `trackedOrdinary: boolean`, plus a private `[track, trigger] = createSignal(undefined, { equals: false })`.

### Decisive source
```ts
const triggerInTransition: () => void = () =>
      startTransition(trigger).then(() => {
        if (inTransition) {
          inTransition.dispose();
          inTransition = undefined;
          // A computation created while a transition was running only ever
          // tracked the transition-scoped source ... otherwise it would never
          // receive further external updates.
          if (!trackedOrdinary) trigger();
        }
      });
c.fn = x => {
      track();                       // keep the internal equals:false signal as the real dependency
      if (Transition && Transition.running) {
        if (!inTransition)
          inTransition = ExternalSourceConfig!.factory(sourceFn, triggerInTransition);
        return inTransition.track(x);
      }
      trackedOrdinary = true;
      return ordinary.track(x);
};
```

**Flow:** registration wraps EVERY new computation's `fn`: each run first touches an internal `{equals:false}` signal (so invalidation is pure Solid), then delegates to the factory-produced source. Outside transitions one `ordinary` source suffices. Inside a transition a SECOND transition-scoped source is created lazily; when its `triggerInTransition` fires post-transition it disposes itself and — if the computation never subscribed to the ordinary source (created during the transition) — fires one extra `trigger()` to force re-run through `ordinary` and re-subscribe.
**Invariant:** Factories COMPOSE onion-style: each later `enableExternalSource` wraps the previous (`oldFactory` inside, new outside), and `untrack` chains likewise — see external-source.spec's beforeEach registering two factories (:53-81). Disposal of the ordinary source must be routed through `onCleanup`. Without the `trackedOrdinary` re-trigger, updates after the second transition are silently lost (test :131-170 pins exactly this).
**Probe:** `grep -c 'trackedOrdinary' packages/solid/src/reactive/signal.ts` → `3` (declaration + set + guard). Decisive test ranges in `test/external-source.spec.ts`: :100-129 "should not throw when rerunning external source in a new transition after disposal" — first transition creates+disposes the transition-scoped source, one microtask later a SECOND `startTransition` must lazily recreate it (`resolves.not.toThrow()`), pinning lazy recreation over eager reuse; :131-175 "should keep receiving external updates after being created during a transition" — a memo created INSIDE `startTransition` tracks only the transition-scoped source, and after the `.then()` disposal/resubscription the NEXT `e.update(2)` must still deliver (comment :161-163 names the pre-fix failure: "silently lost"). **Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "enableExternalSource ExternalSourceConfig triggerInTransition", limit: 10 });
```

## Verdict
Adopt the double-signal bridge pattern for interop layers (RxJS/ETC adapters). Adapt the composition order to your host's plugin system. Omit if no external-source story is needed — but then also drop `untrack`'s ExternalSourceConfig branch.
