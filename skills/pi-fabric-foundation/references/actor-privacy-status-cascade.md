<!-- capsule-v2 -->
# Actor privacy and status resolution — who may read an actor's private data, and in what order is an unknown id identified?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does the provider keep one session's actor mailboxes/definitions/logs private from peers while still resolving ANY participant id for status?

## Owner-only private reads; five-source status cascade
**Path/Symbol:** `src/providers/agents-provider.ts:1877-1884` (`#localActor`), `:1872-1875` (`#actorIsLocal`), `:1335-1359` (`status` cascade), `:1622-1647` (`log` fall-through).
**Signature:** `#localActor(id: string): FabricActorInfo` (throws on non-owner); `stopParticipant(id)` :1920-1952 mirrors the same ladder for stop.
**Data Shape:** participant record carries `local: boolean`, `ownerHostId`, `capabilities[]`; privacy error string: `` `Fabric actor private data is available only from its owner: ${actor.id}` ``.

### Decisive source
```ts
// :1877-1884 — BOTH conditions must hold: manager ownership AND local record
#localActor(id: string): FabricActorInfo {
  const actor = this.actorManager.status(id);
  const participant = this.participants.get(actor.id);
  if (!this.actorManager.owns(actor.id) || participant?.local === false) {
    throw new Error(
      `Fabric actor private data is available only from its owner: ${actor.id}`);
  }
  return actor;
}
// :1335-1358 — status resolves through FIVE sources, most-specific first:
if (this.mainAgent.matches(id)) { /* local info() or mesh participant */ }
try { return this.manager.status(id); }        // 1. local one-shot agent
  catch if !/Unknown Fabric agent/ rethrow
if (this.residency?.hasAgent(id)) ...           // 2. durable resident agent
const known = this.participants.get(id);
if (known && !known.local) return known;        // 3. advertised remote participant
try { return this.actorManager.status(id); }    // 4. persistent actor
  catch if !/Unknown Fabric actor/ rethrow
/* 5. any participant record; else throw Unknown Fabric participant */
```

**Flow:** every private-data action (actorStatus/messages/export/log/clearMessages) funnels through the owner check — a passive peer that merely SEES the actor in its topology still gets the refusal, because `owns()` is false there. The status/log/stop ladders all reuse the identical try/catch-typed fall-through: only `/Unknown Fabric (agent|actor)/` advances to the next source; any other error propagates to the caller.
**Invariant:** visibility of a participant in the shared topology NEVER implies read access to its private state — ownership AND locality are checked together at every private read. Typed-error fall-through is the resolution mechanism: sentinel message regexes distinguish "not mine, keep looking" from real failures. `log` applies the same ladder with actor-first ordering (:1628-1646) since actors retain their last runs after success.
**Probe:** `tests/agents-provider.test.ts:884` ("does not expose passive actor mailboxes, definitions, or logs" — remote-owned actor yields `actors → []` and `actorStatus/messages/export/log` ALL reject with "private data is available only from its owner"); `:1247` pins the final-status throw.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "localActor owns participant privacy actor status", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank#1 resolves `#localActor` :1877-1884 line-exact; `ActorManager.owns` and participant-record builders follow. Drift note: the `status` cascade lives inside the anonymous-body `invoke` switch, which BM25 cannot rank directly — pin it via `#localActor`, whose Path/Symbol header cites the exact switch lines.)

## Verdict
Adopt owner-gated private reads as a hard security boundary for any shared-registry design, and the typed-sentinel fall-through ladder for multi-source id resolution. Adapt which sources exist (drop residency when you have no durable tier); omit nothing — the pairing "public projection vs private state" is the portable idea.
