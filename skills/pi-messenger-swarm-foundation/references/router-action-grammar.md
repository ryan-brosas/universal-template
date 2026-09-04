<!-- capsule-v2 -->
# Router action grammar — how do 40+ model-facing actions dispatch through one entrypoint with aliases and removals?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the canonical action namespace, where do aliases live, and what must a porter know about removed verbs?

## group.op split + registered aliases + loud removals
**Path/Symbol:** `router.ts:executeAction` (:24-233), alias cases `claim`/`unclaim`/`complete` (:164-217), broadcast tombstone (:122-126); CLI natural-grammar mapping `harness/cli.ts:main` switch (:615-912).
**Signature:** `executeAction(action, params, state, dirs, ctx, deliverMessage, updateStatus, _appendEntry?, config?, _signal?)`.
**Data Shape:** action = `group` or `group.op`; task ops default to `list` when op omitted; params validated per-case with `{mode, error}` details.

### Decisive source
```ts
if (group === 'broadcast') {
  return result('Action "broadcast" was removed. Use `pi-messenger-swarm send #channel "message"` instead.',
    { mode: 'broadcast_removed', error: 'removed_action', action });
}
...
case 'complete': {                       // backward-compatible alias → done
  const taskId = params.taskId ?? params.id;
  ...
  return executeTask('done', { ...params, id: taskId }, ...);
}
```
```ts
// send requires an explicit recipient — no implicit broadcast
if (!to || (Array.isArray(to) && to.length === 0) || (typeof to === 'string' && to.trim().length === 0)) {
  return result("Error: send requires 'to'. Use an agent name, agent list, or #channel.", ...);
}
```

**Flow:** registration gate order matters: `join` and `autoRegisterPath` run BEFORE the not-registered check; everything else after. `send` targets: string starting `#` ⇒ channel post; otherwise agent name(s) with the current channel as posting channel. Legacy plan*/work*/review*/crew.* namespaces simply fall to `unknown_action` — only `broadcast` gets a bespoke migration message.
**Invariant:** Aliases normalize into canonical ops by REWRITING params (`{...params, id: taskId}`) rather than re-implementing behavior — porters adding aliases must reuse this rewrite shape or error payloads diverge between spellings. Removed actions answer loudly instead of silently vanishing so older agent habits surface as teachable errors.
**Probe:** direct tests `tests/swarm/router.test.ts::supports claim/unclaim/complete aliases` (:110), `::requires explicit send targets and rejects broadcast` (:317), `::rejects unknown legacy actions` (:349); `grep -c "removed_action" router.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "executeAction broadcast_removed claim unclaim complete requireChannel", limit: 5 });
```

## Verdict
Adopt the group.op grammar + param-rewriting aliases + loud tombstones for removed verbs; adapt your own vocabulary; keep the pre-registration allowlist (join/autoRegisterPath) or agents can never bootstrap.
