<!-- capsule-v2 -->
# Participant routing ladder — how does one message call resolve Main, local agents, actors, and mesh peers without ever broadcasting?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when `agents.steer/followUp/tell` receives an arbitrary participant id, what is the exact resolution order and why must unknown ids throw instead of falling back?

## Four-arm ladder with capability gating and no-broadcast failure
**Path/Symbol:** `src/providers/agents-provider.ts:1653-1750` (`AgentsProvider.routeMessage`); lifecycle delivery rides it via `deliverLifecycle` (:1752-1771).
**Signature:** `routeMessage(id: string, message: string, data: unknown, kind: "steer" | "followUp", context?: FabricInvocationContext, options?: { from?: MeshIdentity; triggerTurn?: boolean }): Promise<FabricAgentMessageResult>`.
**Data Shape:** returns `{ queued: true, messageId, routed: "main" | "local" }` or a control-plane `FabricAgentMessageResult`; throws `Unknown Fabric participant: <id>` after all arms miss.

### Decisive source
```ts
// :1661-1699 — arm 1: Main (stable alias "main"), then remote peers
if (this.mainAgent.matches(id)) {
  if (this.mainAgent.local) { /* deliverAgent({ from, message, delivery: kind, ... }) */ }
  const participant = this.participants.get(this.mainAgent.id);
  if (!participant.capabilities.includes(kind)) {
    throw new Error(`Fabric participant ${participant.id} does not support ${kind}`);
  }
  if (!this.control || participant.controlProtocol === "legacy") {
    return this.actorManager.steerRemote(this.mainAgent.id, message, kind, data);
  }
  return this.control.request(participant.ownerHostId, participant.id, kind,
    { message, data, ...(triggerTurn) }, participant.ownerIdentityId);
}
// :1702-1711 — arm 2: LOCAL one-shot agent
// Local one-shot agent: forward between its turns via the worker's
// steer.jsonl channel, preserving the child's accumulated context.
const result = kind === "steer"
  ? this.manager.steer(id, message, data)
  : this.manager.followUp(id, message, data);
return { queued: true, messageId: result.messageId, routed: "local" };
// :1716-1727 — arm 3: persistent actor mailbox (tell) when owned/local
// :1729-1749 — arm 4: any other advertised participant over the mesh;
//   missing id => throw new Error(`Unknown Fabric participant: ${id}`) — NEVER broadcast.
```

**Flow:** alias-expand (`main` → root session id happens upstream via `#participantAlias`, used by subscribe) → Main arm (local `deliverAgent`, else capability check then v1 control plane or legacy `steerRemote`) → local-agent arm (`manager.steer/followUp` writes the child's `steer.jsonl`) → actor arm (`actorManager.tell` mailbox; only when participant record is absent or local) → mesh arm (capability check again, control-plane request naming `ownerHostId` + `ownerIdentityId`) → loud throw.
**Invariant:** every arm is tried in order and each miss falls through ONLY on `/Unknown Fabric agent|actor/` errors — any other error propagates. An id that resolves nowhere throws; there is deliberately no broadcast/unverified-remote send. Capability withdrawal on a remote Main makes steering throw rather than degrade. `tell` is literally `routeMessage(..., "followUp")` (:1488-1495), so actors consume both delivery kinds through one serial mailbox.
**Probe:** `tests/agents-provider.test.ts:1177` (`routed:"local"` + first line of `<root>/runs/<id>/steer.jsonl` matches `{type:"steer", message}`); `:1247` unknown id rejects with `"Unknown Fabric participant"`; `:1129` `main` alias delivers with `routed:"main"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "routeMessage steer followUp participant control", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered four-arm ladder with typed fall-through errors and the no-broadcast throw; adopt `{queued, messageId, routed}` as the universal acknowledgment shape. Adapt arm vocabulary (Main alias, actor mailboxes, control-plane ops) to your topology. Omit the legacy `controlProtocol === "legacy"` shim when your fleet speaks one protocol. Coverage caveat: the mesh-arm and capability-withdrawal paths are exercised indirectly (`:356` withdraws capabilities); the direct probes above pin the three local arms byte-exact.
