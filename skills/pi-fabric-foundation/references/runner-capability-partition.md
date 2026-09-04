<!-- capsule-v2 -->
# Runner capability partition — which agent actions are legal per runner, and where is the boundary enforced?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when a request names `runner: "pi" | "claude" | "veda"`, what can each runner do, and what must be rejected before any side effect?

## Veda = one-shot prompts only; handoff = Pi-only; models = enumerated or empty
**Path/Symbol:** `src/providers/agents-provider.ts:846-918` (`actorRequest` veda throw :870-874), `:1213-1242` (`executeHandoff` pins `runner:"pi"`), `:1416-1451` (`models` three-way), `:751-758` (`longerTimeoutOverride`); timeout primitive `src/agents/manager.ts:87-102` (`effectiveAgentTimeoutMs`).
**Signature:** `actorRequest(args, context, manager, inheritModel = true): FabricActorRequest`; `longerTimeoutOverride(value: unknown, manager: AgentManager): number | undefined`.
**Data Shape:** runner enum `["pi","claude","veda"]` on run/spawn/create; thinking enum `["off","minimal","low","medium","high","xhigh","max"]`; residency enum `["session","durable"]`.

### Decisive source
```ts
// :870-874 — persistent actors are structurally impossible for a one-prompt runner
if (runner === "veda") {
  throw new Error(
    'The Veda runner does not support persistent actors: Veda executes one headless prompt per invocation. Use a Pi or Claude actor, or agents.run({ runner: "veda" }).');
}
// :1234-1235 — trajectory handoff is pinned to the Pi runtime
request.runner = "pi";
request.sessionSeed = sessionSeed;
// :1421-1426 — unknown model catalog degrades to an ADVISORY EMPTY list
if (runner === "veda") {
  // Veda forwards any -m value to the configured backend; model discovery
  // would require parsing `veda models <backend>`. Return an empty advisory
  // list so callers can still pass model strings directly.
  return [];
}
// :751-757 — only LONGER timeouts are honored at all
const effective = effectiveAgentTimeoutMs(manager.config.timeoutMs, value);
return effective > manager.config.timeoutMs ? effective : undefined;
```

**Flow:** every mutating entry coerces args through `runRequest` (:760-811) / `actorRequest` — enum-or-default for runner/thinking/transport, `stringArray` silently drops non-string tool entries, schema objects must be plain objects. The veda actor check fires inside the coercion (before any create/spawn side effect). Handoff requires an explicit non-empty `model` string TWICE (scheduling :1202-1203 and execution :1218-1219), then force-overrides `request.runner = "pi"` so a caller-supplied runner cannot smuggle through. Model enumeration per runner: claude from the installed runtime, pi from the extension model registry (failure → `[]`), veda → `[]` by design.
**Invariant:** capability boundaries live in ONE provider layer, enforced at coercion time with loud typed throws — not scattered across managers. Timeout overrides can only EXTEND the configured default (shorter values are silently ignored, pinned by test). Model-list emptiness means "no catalog; pass-through still works", never "no models exist".
**Probe:** `tests/agents-provider.test.ts:836` ("ignores actor timeout overrides below the configured default" — definition lacks `timeoutMs` for 240_000 vs default, keeps 7_200_000); `tests/worker-e2e.test.ts:222` rejects steering of veda children; `:208` rejects recursion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "runRequest actorRequest inherited model coercion provider boundary", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves both coercers rank#1/#2 line-exact :846-918 and :760-811.)

## Verdict
Adopt the single-layer capability partition: validate runner-specific legality in one coercion pass with explicit throws naming alternatives, force-pin privileged flows (handoff) to their required runtime regardless of input, and treat model catalogs as advisory. Adapt the runner vocabulary and enum sets; omit veda semantics if you have no headless one-shot dialect — but keep SOME runner that cannot persist, to see where your own boundaries must throw.
