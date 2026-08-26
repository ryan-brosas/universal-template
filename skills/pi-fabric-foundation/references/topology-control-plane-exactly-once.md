<!-- capsule-v2 -->
# Control-plane exactly-once commands — how do you route steer/stop to a remote agent over an at-least-once mesh without double-executing?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for command delivery where the transport (mesh event log) can replay events after restart or compaction?

## Connected graph-selected seam
**Path/Symbol:** `src/topology/control-plane.ts` — `FabricControlPlane.request` (:135-182), `#acceptCommand` (:246-340), `#acceptAcknowledgement` (:226-244), `#drain` (:211-224), `#cleanupSeen` (:342-354), `controlSeenKey` (:42-44).
**Signature:** `request(ownerHostId, targetId, operation, input?, ownerIdentityId?)` → `{ queued: true, messageId, routed: "mesh", acknowledged: true }`; throws on ack timeout (`ackTimeoutMs`, floor `pollMs*4`) or owner rejection; `start(handler)` registers the owner-side executor.
**Data Shape:** command v1 `{ version: 1, commandId: uuid, targetId, operation: "steer"|"followUp"|"stop", replyTo, message?, data?, triggerTurn?, requestedAt }`; seen-record `format: 1` `{ hostId, commandId, targetId, expiresAt, acceptance? }` stored at key `topology/control-seen/sha256(hostId\0commandId)` — the host id is hashed INTO the key so each host self-certifies its own dedupe namespace.

### Decisive source
```ts
    let claim;
    try {
      claim = await this.mesh.put({
        key,
        value: {
          format: 1,
          hostId: this.options.hostId,
          commandId: command.commandId,
          targetId: command.targetId,
          expiresAt: now + this.#ackTimeoutMs,
        } satisfies FabricControlSeenRecord,
        identity: this.identity,
        ifVersion: 0,                        // claim ONLY if absent
      });
    } catch {
      const raced = controlSeenRecord(this.mesh.get(key)?.value);
      if (
        raced?.hostId === this.options.hostId &&
        raced.commandId === command.commandId &&
        raced.targetId === command.targetId
      ) {
        // lost the create race → answer from whatever record won, WITHOUT running
        await this.#publishAcknowledgement(
          command,
          raced.acceptance ?? {
            accepted: false,
            error: "Fabric control outcome is indeterminate after concurrent claim",
          },
        );
      }
      return;
    }
```

**Flow:** requester publishes the command then parks a per-commandId pending entry with a timeout timer; owner's poll loop drains the retained log by offset+sequence, filters `event.to === hostId`, and for each fresh command runs the ladder — freshness window first (`|now − requestedAt| > ackTimeoutMs` ⇒ reject "expired", also rejecting clock-skewed futures), then duplicate check against the seen-record (a hit re-publishes the RECORDED acceptance verbatim — replay after restart returns the original outcome instead of re-running), then CAS seen-claim at `ifVersion: 0` (concurrent twin gets the indeterminate path above), THEN handler execution, then a second CAS write (`ifVersion: claim.version`) that stamps `acceptance` before the ack is published — so any replay can always recover the true outcome from the durable record. Acks resolve the parked promise only when `commandId`, `targetId`, AND `event.from.id === pending.ownerIdentityId` all match.
**Invariant:** exactly-once EXECUTION over at-least-once DELIVERY — the seen-record is claimed durably BEFORE the handler runs and completed with the acceptance AFTER; every interrupted state resolves to an explicit outcome ("indeterminate after owner restart/concurrent claim"), never silence and never re-execution; forged/mismatched-identity acks are ignored; `close()` final-drains the log once and settles every still-pending request with `accepted: false`.
**Probe:** `tests/control-plane.test.ts:123` ("recovers an unexpired command published before owner startup"), `:159` ("rejects an interrupted durable claim as indeterminate after restart"), `:212` ("does not re-execute a command republished after owner restart"), `:83` ("ignores an acknowledgement forged by a different mesh identity").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricControlPlane request acceptCommand acknowledgement seen commandId", limit: 5, fields: ["signature", "name", "file"] });
```
