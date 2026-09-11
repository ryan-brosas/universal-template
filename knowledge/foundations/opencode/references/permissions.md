<!-- capsule-v2 -->
# Permission model — how tool approvals resolve and suspend

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a tool call get allow/deny/ask, and how does "ask" suspend and resume?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/permission/index.ts`: `evaluate` (:28-37), `Service` (:40), `fromConfig` (:186), `merge` (:200), `disabled` (:204), `visibleTools` (:216).
**Signature:** `evaluate(permission: string, pattern: string, ...rulesets: PermissionV1.Ruleset[]): PermissionV1.Rule`.
**Data Shape:** rulesets are arrays of `{permission, pattern, action}` rules; returns the matched rule or the default `{action:"ask", permission, pattern:"*"}`.

### Decisive source
```ts
export function evaluate(permission: string, pattern: string, ...rulesets: PermissionV1.Ruleset[]): PermissionV1.Rule {
  return (
    rulesets
      .flat()
      .findLast((rule) => Wildcard.match(permission, rule.permission) && Wildcard.match(pattern, rule.pattern)) ?? {
      action: "ask",
      permission,
      pattern: "*",
    }
  )
}
```

**Flow:** rule layers (user config → project config → session approvals) append; `findLast` makes the LAST matching rule authoritative → later, more specific config overrides earlier. No match → fail toward `ask`, never allow. "Ask" suspends the tool call as a pending request (Effect Deferred); the human reply resolves it — reject feeds `CorrectedError({feedback})` back to the model; approve appends to the `approved` ruleset (always-allow = ruleset growth, not a side-channel).
**Invariant:** a single "ask" pattern creates ONE pending request covering all patterns — no partial allows leak mid-request; shutdown finalizer fails all pending with `RejectedError` so nothing hangs.
**Probe:** `packages/opencode/test/permission/next.test.ts` (rejectAll/waitForPending drive the ask→reply→resolve loop; `permission/arity.test.ts` pins `evaluate` wildcard matching).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Permission evaluate ruleset findLast ask", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ruleset-evaluated, last-wins, fail-toward-ask permission model with Deferred suspension and rejection-as-feedback; adapt rule-layer ordering and the pending-request UI surface to host; omit the opencode-specific `Effect`/`Context.Service` wiring unless the target uses Effect.
