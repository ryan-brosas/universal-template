<!-- capsule-v2 -->
# Inbound control-command boundary — what may a mesh peer do to MY participants, and how does the owner answer?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when a remote host delivers a `steer/followUp/stop` command at my session, what is the acceptance contract that keeps ownership and capability boundaries intact?

## Mirrored resolution with explicit non-acceptance reasons
**Path/Symbol:** `src/providers/agents-provider.ts:1773-1844` (`AgentsProvider.acceptControl`).
**Signature:** `acceptControl(command: FabricControlCommand, from: MeshIdentity): Promise<FabricControlAcceptance>` where acceptance is `{ accepted: true, messageId: command.commandId | result.messageId }` or `{ accepted: false, error: string }` — never a throw across the wire.
**Data Shape:** `FabricControlCommand { version: 1, commandId, targetId, operation: "steer"|"followUp"|"stop", replyTo, message?, data?, triggerTurn?, requestedAt }`; `from` is the requesting mesh identity (used verbatim as delivery `from` for local Main).

### Decisive source
```ts
// :1777-1802 — stop arm: local agents first...
if (command.operation === "stop") {
  try {
    await this.manager.stop(command.targetId);
    this.participants.scheduleRefresh();
    return { accepted: true, messageId: command.commandId };
  } catch (error) {
    if (!(error instanceof Error && /Unknown Fabric agent/.test(error.message))) {
      return { accepted: false, error: error instanceof Error ? error.message : String(error) };
    }
  }
  // ...then actors, but ONLY while locally owned:
  const actor = this.actorManager.status(command.targetId);
  const ownership = this.participants.get(actor.id);
  if (ownership && !ownership.local) {
    return { accepted: false,
      error: `Participant ${actor.id} is owned by ${ownership.ownerHostId}` };
  }
  await this.actorManager.stop(actor.id);
}
// :1804-1805 — message arms gate on emptiness BEFORE routing
const message = command.message?.trim();
if (!message) return { accepted: false, error: "Fabric control message must not be empty" };
// :1806 — local Main accepts and uses the PEER identity as delivery "from"
if (this.mainAgent.local && this.mainAgent.matches(command.targetId)) {
  const result = this.mainAgent.deliverAgent({ from, message, delivery: command.operation, ... });
```

**Flow:** stop → try local agent; fall through only on unknown-agent → try actor with an OWNERSHIP REFUSAL when its participant record says remote → otherwise accept. steer/followUp → trim-empty refusal → local Main (`from` = peer identity, so replies route back to the sender) → local agent (`manager.steer/followUp`) → owned actor (`actorManager.tell`) → final `Owner does not control Fabric participant <id>` refusal.
**Invariant:** every failure is an EXPLICIT `{accepted:false, error}` naming the reason — ownership conflicts name the owning host, unknown targets get a distinct final refusal, empty messages are rejected before any side effect. Only `/Unknown Fabric (agent|actor)/` errors advance the ladder; real failures (spawn failures, IO errors) are returned as refusals, never swallowed into fall-through. The messageId echoed on success is `command.commandId` for stops but the routed message id for deliveries.
**Probe:** `tests/agents-provider.test.ts:1195` (`acceptControl({operation:"followUp", targetId:<local handle>})` → `{accepted:true}` + first `steer.jsonl` line `{type:"follow_up", message}`). Coverage caveat: the ownership-refusal and empty-message branches have NO direct test in-repo (grep for "is owned by"/"Owner does not control" over tests = 0 hits) — porters must treat those branches as source-derived only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "acceptControl stop command owner", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank#2 resolves `AgentsProvider.acceptControl` :1773-1844; rank#1 is the ResidentHost counterpart `src/residency/host.ts:311-358`.)

## Verdict
Adopt the mirrored inbound boundary: same participant vocabulary as outbound routing, explicit typed refusals instead of throws, peer identity threaded as delivery source. Adopt the ownership check as the security boundary it is — a host must refuse to act on participants whose participant record names another owner. Adapt operation set/refusal strings; omit the legacy steering shim if your fleet has no pre-control-plane peers.
