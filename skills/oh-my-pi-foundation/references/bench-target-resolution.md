<!-- capsule-v2 -->
# Bench target resolution — how do you resolve fuzzy model selectors for benchmarks so ambiguous ids never silently land on unauthenticated providers?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the exact redirect ladder in `resolveAuthenticatedAlternative`, and why do benchmarks resolve against the FULL catalog first?

## Authenticated-equivalent fallback
**Path/Symbol:** `packages/coding-agent/src/cli/bench-runtime.ts:` module doc (:1–9), `BenchModelRegistry` (:37–43), `pickHighestPriorityProvider` (:79–87), `resolveAuthenticatedAlternative` (:97–121), `resolveBenchTargets` (:129–185, full-catalog comment :139–142); shared by `omp bench` + `omp if-bench` (extracted from bench-cli.ts in 5092fe9e2f).
**Signature:** `resolveBenchTargets(selectors, modelRegistry, settings, writeStderr): BenchTarget[]`; `StreamSimpleFn = (model, context, options?) => AssistantMessageEventStream` is the test injection seam.
**Data Shape:** `BenchTarget {selector, model, thinking}`; redirect emits a stderr warning naming both the skipped provider and the pinned-selector escape hatch.

### Decisive source
```ts
if (!modelRegistry.hasConfiguredAuth) return undefined;
// A pinned `provider/...` selector is authoritative; never redirect off it.
if (selector.trim().toLowerCase().startsWith(`${model.provider.toLowerCase()}/`)) return undefined;
if (modelRegistry.hasConfiguredAuth(model)) return undefined;
const seen = new Set<string>();
...
for (const candidate of modelRegistry.getAll()) {
	if (candidate.id === model.id) consider(candidate);      // SAME-ID equivalents only
}
return pickHighestPriorityProvider(authenticated, providerOrder);   // native/OAuth outrank mirrors
```

**Flow:** each selector resolves against `modelRegistry.getAll()` (full catalog — using the CLI's authenticated default would silently redirect NON-equivalent bare ids and suppress the cross-provider warning) → if the resolved provider lacks credentials and the selector wasn't provider-pinned, find same-id models under authenticated providers, pick the highest-priority transport, warn on stderr ("benchmarking X instead. Pin … to force it") → any unresolved selector collects into one aggregate throw listing all failures.
**Invariant:** Redirects are SAME-ID only (never "a similar model that happens to work"), opt-out-able via explicit `provider/id` pins honored even when unauthenticated, and priority-ranked (native/OAuth transports beat mirrors) so benchmarked endpoints are the ones users actually serve. The `hasConfiguredAuth` capability itself is optional on the registry interface — absent ⇒ no redirect path at all.
**Probe:** No dedicated unit test file drives this module directly; behavior verified byte-exact by read at pin: pin-gate @bench-runtime.ts:105, same-id filter @:118, single `hasConfiguredAuth?.(candidate)` @:114, scoreboard tie-break twin `(b.turnsPassed - a.turnsPassed || b.actionsPassed - a.actionsPassed || meanTurnMs(a) - meanTurnMs(b))` @board.ts:223. Coverage caveat recorded per workflow gate 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveAuthenticatedAlternative resolveBenchTargets", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: rank-1×2 exact — `resolveAuthenticatedAlternative bench-runtime.ts:97-121`, `resolveBenchTargets :129-185`.

## Verdict
Adopt catalog-wide resolution + same-id authenticated fallback for any multi-provider tool runner; keep the explicit-pin override and the loud warning. Adapt provider-priority ranks to your registry. Omit thinking-level resolution specifics unless you mirror oh-my-pi's reasoning ladder.
