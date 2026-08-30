<!-- capsule-v2 -->
# PermissionV2 ask/assert/reply machine — how do pending approvals layer with saved approvals and configured denies?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does a v2 tool call resolve allow/deny/ask against agent rules + saved project approvals, and how do replies cascade across a session?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/permission.ts`: `evaluate` (:44-51), `configured` (:104-110), `evaluateInput` (:118-124), `create` (:135-153), `ask` (:155-159), `assert` (:161-180), `reply` (:182-224), finalizer (:85-92).
**Signature:** `assert: (input: AssertInput) => Effect<void, BlockedError | CorrectedError | SessionV2.NotFoundError>`; `reply: (input: ReplyInput) => Effect<void, NotFoundError>`.
**Data Shape:** `AssertInput {id?, sessionID, action, resources[], save?, metadata?, source?, agent?}`; pending map `Map<ID, {request, agent?, deferred: Deferred<void, DeclinedError | CorrectedError>}>`; saved approvals are per-project DB rows `{action, resource}` with effect allow.

### Decisive source
```ts
const missingAgentPermissions: Permission.Ruleset = [{ action: "*", resource: "*", effect: "deny" }]
...
const evaluateInput = EffectRuntime.fnUntraced(function* (input: AssertInput) {
  const rules = yield* configured(input.sessionID, input.agent)
  if (denied(input, rules)) return { effect: "deny" as const, rules }
  const all = [...rules, ...(yield* savedRules())]
  const effects = input.resources.map((resource) => evaluate(input.action, resource, all).effect)
  const effect: Permission.Effect = effects.includes("deny") ? "deny" : effects.includes("ask") ? "ask" : "allow"
  return { effect, rules: all }
})
```
A configured deny is checked BEFORE saved rules are appended, so a saved allow can never override a configured deny (test-pinned):
```ts
yield* setRules([{ action: "bash", resource: "*", effect: "deny" }])
expect(yield* service.ask(assertion({ action: "bash", resources: ["pwd"] }))).toMatchObject({ effect: "deny" })
```

**Flow:** `ask()` evaluates and only queues when the effect is ask — returns `{id, effect}` immediately, never blocks. `assert()` is `uninterruptibleMask`: deny → `BlockedError` carrying only the RELEVANT (action-matching) rules; allow → return; ask → `create` (uninterruptible: Deferred + `pending.set` + publish `Event.Asked` with onError rollback; duplicate pending ID → die) then `restore(Deferred.await(...))` — a `DeclinedError` is converted to a DIE (`EffectRuntime.die`), a `CorrectedError` (reject WITH feedback) propagates as a typed error; `ensuring` deletes the pending entry. `reply()` is uninterruptible: `reject` fails the deferred AND cascades rejection to every OTHER pending request of the same session (each also published as Replied); `always` with save resources persists them via `saved.add`, succeeds the deferred, then re-evaluates every remaining pending request (any session) against configured+saved rules and auto-succeeds those now fully allowed, publishing Replied always for each. Shutdown finalizer fails all pending with `DeclinedError`.
**Invariant:** a missing agent resolves to deny-all (not ask); a declined assert is a defect in the caller's world, never a catchable error; reject cascades session-wide; saved-allow never beats configured-deny; duplicate pending IDs die.
**Probe:** `packages/core/test/permission.test.ts` (11 it.effect: ask-queues-only-on-ask, explicit-agent override, saved-vs-configured precedence, resolve-once, decline-as-Die via `Cause.isDieReason`, saved rows persisted + removed, cascade behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "PermissionV2 assert reply pending Deferred Asked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-stage evaluation (configured-deny short-circuit before saved layer), the ask/assert split (non-blocking probe vs blocking gate), decline-as-defect semantics, session-wide reject cascade, and always-reply re-evaluation sweep. Adapt the storage of saved approvals and event publication to your host. Omit Effect/Schema specifics. Drift note: this capsule covers the v2 service lifecycle; the pass-1 `permissions.md` capsule covers the v1 config-side evaluate ladder — the `evaluate` findLast semantics are shared and not re-stated here.
