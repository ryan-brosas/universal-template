<!-- capsule-v2 -->
# Participant presence directory — how do multiple hosts share one mesh without two of them owning the same participant?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what makes a participant record trustworthy, and who wins when a participant id collides across hosts?

## Hashed keys + host-lease staleness + CAS takeover ladder
**Path/Symbol:** `src/topology/participant-directory.ts:ParticipantDirectory` (:224-622; refresh :288-302, #refresh :486-616, list :304-380, self :387-423, quiesce :458-463, close :465-484); key derivation `keyFor` (:20-21); validators `participantFromEntry`/`hostFromEntry` (:40-92).
**Signature:** heartbeat 5s (floor 100ms), lease 15s (`leaseMs ≥ 2×heartbeat`, enforced in ctor); `keyFor(prefix, id) = prefix + sha256(id)`; records `{format:1, kind:"root"|"agent"|"actor", rootId, ownerHostId, ownerIdentityId, status, runner, transport, capabilities[], controlProtocol:"v1"|"legacy", …}`.
**Data Shape:** three mesh namespaces: `topology/participants/<sha256(id)>`, `topology/hosts/<sha256(hostId)>` (with `expiresAt`), plus LEGACY read-compat `sessions/<sessionId>` and `actors/<sessionId>/<actorId>`.

### Decisive source
```ts
// self-certifying: a record is invalid unless its KEY hashes its OWN id
if (!kind || typeof value.id !== "string" ||
    entry.key !== keyFor(PARTICIPANT_PREFIX, value.id) || ...
    entry.updatedBy.id !== value.ownerIdentityId) return undefined;
```
```ts
// takeover: an occupied id moves only when its owner's lease has EXPIRED
if (occupiedParticipant && occupiedParticipant.ownerHostId !== this.options.hostId) {
  const owner = ownerEntry && hostFromEntry(ownerEntry);
        if (
          owner &&
          owner.expiresAt >= now &&
          owner.identity.id === occupiedParticipant.ownerIdentityId
        ) {
          continue;   // still owned by a live host
        }
}
await this.mesh.put({ key, value: record, identity, ...(occupied ? { ifVersion: occupied.version } : {}) })
      }).catch((error: unknown) => {
        const latest = this.mesh.get(key);
        const latestParticipant = latest && participantFromEntry(latest);
        if (latestParticipant && latestParticipant.ownerHostId !== this.options.hostId) return;
        throw error;
      });
```

**Flow:** every refresh re-derives desired records from registered snapshot sources (stripping non-operational `task/text/error` fields — prompts/results/errors NEVER enter shared state), stamps ownership + `controlProtocol:"v1"` → publishes the host lease FIRST (`expiresAt = now + leaseMs`) so later staleness checks see a live self → writes changed participants under `ifVersion` CAS; deletes participants that vanished from sources → `list()` treats a participant as stale when its owner-host record is missing/expired/identity-mismatched and hides it unless `includeStale`; legacy `sessions/*` roots are read with a 15s freshness window and never shadow live v1 records. Heartbeat doubles as the recovery path: initial-publish failure at startup still starts the interval, so the host joins the mesh once the contended lock clears. Teardown order: `quiesce()` first republishes all local records with `capabilities: []` (withdraw remote-control BEFORE dying), deletes the legacy session pointer, then refreshes; `close()` clears the timer, drains in-flight refreshes, then CAS-deletes owned participants, the legacy session entry, and finally the host lease.
**Invariant:** one live owner per participant id (lease-guarded takeover, not last-write-wins); identity binding (`updatedBy.id === ownerIdentityId`) plus hashed-key self-certification rejects forged or relocated entries; a crashed host's participants become invisible via lease expiry WITHOUT anyone writing tombstones.
**Probe:** `tests/participant-directory.test.ts:149` ("withdraws control capabilities before releasing its live host lease" — post-quiesce `capabilities: []` and legacy session key gone while lease alive), `:174` ("does not claim an actor still owned by a live legacy root"), `:359` ("hides every participant owned by an expired host lease"), `:302` ("keeps one live execution owner for a colliding participant id"), `:416` ("recovers via heartbeat when the initial publish fails at startup").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ParticipantDirectory quiesce expiresAt ifVersion ownerHostId legacyRootFromEntry scheduleRefresh", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hashed-key self-certification, lease-based staleness, capability-withdrawal-before-teardown ordering, and the CAS-takeover-with-lost-race-tolerance; adapt prefixes, heartbeat/lease values, and the legacy vocabulary to your mesh; omit the pi runner/transport enums. Direct tests cited; graph coverage clean.
