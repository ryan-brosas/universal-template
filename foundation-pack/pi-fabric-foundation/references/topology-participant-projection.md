<!-- capsule-v2 -->
# Participant projection records — how do live agents/actors become topology participants with capability sets derived from state?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for projecting `AgentRunRecord | AgentHandleInfo` and `FabricActorInfo` into `FabricParticipantRecord`s for the mesh?

## Connected graph-selected seam
**Path/Symbol:** `src/topology/records.ts` — `agentParticipantRecords` (:9-60), `actorParticipantRecord` (:62-92), `isAgentRunRecord` guard (:5-7).
**Signature:** `agentParticipantRecords(records, rootId, ownerHostId, ownerIdentityId, parentId, firstSeen: Map<string, number>)` → records; the `firstSeen` map is MUTATED across calls so `startedAt` stays stable for previously-seen ids.
**Data Shape:** participant `format: 1` `{ id, kind: "agent"|"actor", rootId, ownerHostId, ownerIdentityId, parentId, name, status, residency?, runner?, transport?, capabilities[], controlProtocol: "v1", … }`.

### Decisive source
```ts
    const active = record.status === "queued" || record.status === "running";
    participants.push({
      ...
      capabilities: [
        ...(active ? (["steer", "followUp", "stop"] as const) : []),
        ...(record.attachCommand ? (["attach"] as const) : []),
        ...(record.recursive ? (["fabric"] as const) : []),
      ],
      ...
      controlProtocol: "v1",
```

**Flow:** agent records whose id is already claimed by an ACTOR (`record.actorId`) are SKIPPED entirely — the actor's own projected record wins, preventing a double topology entry for the same logical worker. Actor-derived capabilities are status-driven too (stopped ⇒ no steer/followUp/stop; `fabric` capability requires runner `"pi"` AND extensions not disabled). `startedAt` falls back to first-observed wall time when a run record lacks it; run stats (`turns/toolCalls/usage`) ride along only for full run records.
**Invariant:** capabilities are DERIVED, never declared — a paused/finished agent silently loses its control surface (consumers like the lifecycle broker gate delivery on these); ownership fields are always stamped so remote hosts can route commands (control-plane) and validate lifecycle event owners; unknown-shape records degrade to handle-info semantics via the `"startedAt" in record` structural check.
**Probe:** direct tests live in `tests/control-plane.test.ts` + `tests/participant-directory.test.ts` consumers rather than a dedicated suite; source pins :26-27 (actor-skip), :27+41-45 (active-gated capabilities), :83 (pi-runner fabric gate). Coverage caveat stated honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "agentParticipantRecords actorParticipantRecord capabilities FabricParticipantRecord", limit: 5, fields: ["signature", "name", "file"] });
```
