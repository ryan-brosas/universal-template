<!-- capsule-v2 -->
# Durable actor activation compensation — how do you transfer ownership of a long-lived worker to a hidden resident host without orphaning it?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the exact create→cede→ensure choreography (and its rollback) that moves an actor from the live session to Fabric's durable resident host?

## Cede first, ensure second, reclaim on failed ensure
**Path/Symbol:** `src/providers/agents-provider.ts:1855-1870` (`AgentsProvider.#activateDurableActor`), gate `#resident()` :1846-1853; primitives `src/actors/manager.ts:337-353` (`ActorManager.cede`), `:355-362` (`reclaim`); remote side `src/residency/client.ts:123-126` (`ResidencyClient.ensureActor`). Call sites: `create` :1460-1471, `import` :1597-1615, `remove` :1581-1588.
**Signature:** `async #activateDurableActor(actor: FabricActorInfo): Promise<void>`; `cede(id)` / `reclaim(id): void`; `ensureActor(id): Promise<void>`.
**Data Shape:** residency enum `"session" | "durable"` on spawn/create requests; durable requires a trusted mesh-persisted project (`#resident()` throws `"Durable residency requires a trusted project with Fabric mesh persistence enabled"` when the client is absent).

### Decisive source
```ts
// :1855-1870 — the whole compensation ladder
await this.actorManager.cede(actor.id);
await this.participants.refresh();          // topology now shows the host as owner
try {
  await residency.ensureActor(actor.id);    // resident host claims + resumes it
} catch (error) {
  try {
    await residency.removeActor(actor.id);  // scrub partial remote state...
  } catch {
    this.actorManager.reclaim(actor.id);    // ...or take the actor back locally
  }
  await this.participants.refresh().catch(() => undefined);
  throw error;                              // caller still sees the real failure
}
```

**Flow:** request validated with `residency:"durable"` → `#resident()` gate (loud throw, not silent local fallback) → `actorManager.create()` locally → `#activateDurableActor`: cede (release local ownership; ActorManager stops executing/mutating it — its own tests pin that mutation is owner-gated) → `participants.refresh()` publishes the ownership change → `ensureActor` asks the resident host to claim it → success ends with the actor alive under the resident host, mailbox intact. Failure → try `removeActor` to erase half-claimed remote state; if even THAT fails, `reclaim` restores local ownership so the actor is never lost in limbo; refresh best-effort; rethrow the original error.
**Invariant:** at every instant the actor has exactly ONE accountable owner. The rollback order matters: remove-before-reclaim means a successful remote scrub leaves the actor cleanly gone, and only an unreachable resident triggers reclaim. Errors are rethrown AFTER compensation so callers can distinguish "not created" from "created but local". The same ladder runs for template `import` (:1597-1615), and `remove` routes by ownership: durable-and-not-owned goes to `residency.removeActor`, else local removal.
**Probe:** `tests/residency.test.ts:234` (real `actors.cede(actor.id)` + `client.ensureActor` then Main shutdown; messages keep flowing to the resident host) and `tests/agent-manager.test.ts`/`tests/actor-manager.test.ts:84` ("executes and mutates actors only while this host owns them") pin the owner-gate semantics cede relies on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "activateDurableActor cede reclaim ensureActor", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves all three primitives line-exact: cede :337-353, reclaim :355-362, ensureActor :123-126.)

## Verdict
Adopt the cede→refresh→ensure→compensate ladder verbatim for any ownership-transfer-to-daemon flow (resident runners, queue workers, scheduled jobs). Adopt "remove-then-reclaim" as the two-sided rollback and the loud gate when residency infrastructure is missing. Adapt the transport (mesh control plane here); omit the specific actor/mailbox semantics if your workers are stateless.
