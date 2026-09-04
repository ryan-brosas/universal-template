<!-- capsule-v2 -->
# Actor ownership ladder — how do multiple hosts share one actor registry without double-running or losing an actor at handoff?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** when two processes can see the same persistent actors.json, what decision function and transition choreography keep exactly one owner executing each actor?

## Decision ladder + abort-and-reject on loss
**Path/Symbol:** `src/actors/manager.ts` → `#ownershipDecision` (:1966-1977), `#refreshOwnership` (:1979-2014), `cede` (:337-353), `reclaim` (:355-362), `#withRegistryLock` (:1705-1762), `#syncActorsFromRegistry` (:1787-1819).
**Signature:** `#ownershipDecision(id): boolean`; `cede(id): Promise<FabricActorInfo>`; `reclaim(id): FabricActorInfo`.
**Data Shape:** per-actor caches: `#locallyCreated: Set`, `#ceded: Set`, `#ownership: Map<id,boolean>`; registry file `{format:1, actors:[...]}` guarded by a mkdir-lock (`actors.json.lock/owner` = `token\npid\ncreatedMs`); residency ∈ `"session"|"durable"`.

### Decisive source
```ts
#ownershipDecision(id: string): boolean {
  if (this.#ceded.has(id)) return false;                       // 1. explicit cede wins
  const actor = this.#actors.get(id);
  if (actor && this.#claimResidency && actor.rootId !== this.#rootId) return false;
  const decision = this.#canManageActor?.(id);                 // 2. host predicate (participant dir)
  if (decision !== undefined) return decision;
  if (this.#locallyCreated.has(id)) return true;               // 3. created here
  if (actor && this.#claimResidency !== undefined)
    return actor.residency === this.#claimResidency;           // 4. residency claim match
  return this.#canManageActor === undefined;                   // 5. single-host default
}
```

**Flow:** every mutating path calls `#refreshOwnership()` → transitions true→false **abort the in-flight run and reject every queued item** (ownership moved) → acquiring ownership of a persistent registry triggers one full reload under `#reloadingOwnership` re-entry guard (clear + `#loadActors`) → saves go through `#saveActors`, which rewrites only owned+removed ids while **preserving foreign records verbatim** via read-modify-write under the mkdir lock with stale-lock recovery (age >30s AND pid dead, token re-read to confirm) — `cede()` additionally rejects queued items with "residency transferred" and leaves status idle so another host picks it up.
**Invariant:** the ladder is strictly ordered — an explicit `cede` beats everything, and a host that cannot decide must answer "not mine"; registry writes never drop foreign rows. A porter who treats "created elsewhere" as ownable (skipping rule 2's tri-state undefined) double-runs durable actors.
**Probe:** `tests/actor-manager.test.ts:84` ("executes and mutates actors only while this host owns them"), :101 ("does not claim a durable actor from another root"), :134 ("preserves current remote actor records when saving a locally owned actor").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ownershipDecision canManage cede reclaim", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-rule ladder and the abort-and-reject loss choreography for any shared registry of executable entities; adapt the host predicate to your membership directory; omit the mkdir-lock if your store already CAS-guards writes. Direct tests pin all three contested cases — no coverage caveat.
