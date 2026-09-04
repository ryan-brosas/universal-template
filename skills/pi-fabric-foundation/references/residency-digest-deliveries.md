<!-- capsule-v2 -->
# Residency digest addressing — how do two processes that never share a socket agree on file/mailbox paths and drain cross-root deliveries exactly once?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how are resident-host identity, residency root, and delivery keys derived from a rootId, and what gates a drained delivery before it reaches the Main agent?

## SHA-256(rootId)-derived namespace + validated mesh-keyed delivery drain with version-pinned delete
**Path/Symbol:** `src/residency/protocol.ts` whole (:1-123): `RESIDENT_HOST_FORMAT = 1` (:7), `residentHostId` (:13-14), `residentRoot` (:16-17), `residentDeliveryPrefix` (:19-20), `ResidentDeliveryRecord` (:113-123). Consumer: `src/residency/client.ts#drainDeliveries` (:368-377) + `#deliver` (:379-403); host binds the same prefix at `src/residency/host.ts:143`. Direct tests `tests/residency.test.ts:323-408`.
**Signature:** `residentHostId(rootId): "resident:<24 hex>"`, `residentRoot(meshRoot, rootId): <meshRoot>/residency/<32-hex>`, `residentDeliveryPrefix(rootId): "residency/deliveries/<32 hex>/"`; `#deliver(entry: MeshStateEntry): Promise<void>`.
**Data Shape:** every wire object carries `format: typeof RESIDENT_HOST_FORMAT` (9 interfaces in protocol.ts stamp it); delivery record `{format, id, rootId, from: MeshIdentity, delivery: "steer"|"followUp", triggerTurn: boolean, message, data?, createdAt}`.

### Decisive source
```ts
const digest = (value: string): string => createHash("sha256").update(value).digest("hex");
export const residentHostId = (rootId) => `resident:${digest(rootId).slice(0, 24)}`;
export const residentDeliveryPrefix = (rootId) =>
  `${RESIDENT_DELIVERY_PREFIX}${digest(rootId).slice(0, 32)}/`;   // ":20"

// client.ts #deliver — SEVEN-field validation gate before any side effect:
if (value.format !== RESIDENT_HOST_FORMAT || value.rootId !== this.options.config.rootId ||
    typeof value.id !== "string" || typeof value.message !== "string" ||
    (value.delivery !== "steer" && value.delivery !== "followUp") ||
    typeof value.triggerTurn !== "boolean" || typeof value.from !== "object" ||
    value.from === null || entry.updatedBy.id !== this.hostId)
  return;                                    // malformed/foreign ⇒ silent drop
this.options.mainAgent.deliverAgent({ from: value.from, message: value.message,
  delivery: value.delivery, triggerTurn: value.triggerTurn, ... });
await this.options.mesh.delete({ key: entry.key, ifVersion: entry.version });
```

**Flow:** host and client independently derive identical namespaces from ONLY the shared rootId — no handshake carries addresses; deliveries are written into the mesh store under the digest prefix (host :423/:430 key form `${prefix}${id}`), and the client polls on an interval timer (unref'd, :83-88) draining via `mesh.listAll(prefix)`; each record is validated against ALL fields plus authorship (`updatedBy.id === this.hostId` — only your own resident host's writes count), delivered to Main through the same deliverAgent path as live participants, then deleted with a compare-and-delete (`ifVersion`) so a concurrent redelivery cannot double-fire.
**Invariant:** digest length differs per purpose (hostId 24, root dir 32, delivery prefix 32) — they are NOT one constant; drain is single-flight (`#drainingDeliveries` latch ×5 references) and gated on `mainAgent.local` + not-closed; test :397-400 documents that delete lags deliver (locked write) so drains must poll to empty rather than assert synchronously.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "digest(rootId).slice(0, 24)" src/residency/protocol.ts'` → line 14; `grep -c "#drainingDeliveries" src/residency/client.ts` → 5; `grep -n "await this.options.mesh.delete({ key: entry.key, ifVersion: entry.version })" src/residency/client.ts` → line 402; e2e pins in tests/residency.test.ts: `grep -n "const prefix = residentDeliveryPrefix(state.identity.id)" tests/residency.test.ts` → 385, queue-until-Main-resumes `expect(state.deliveries).toEqual([])` :387 → post-start delivery matchObject :391-396 → drained-to-zero :399-400.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "resident delivery prefix drain mesh deliveries residency", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `residentDeliveryPrefix` src/residency/protocol.ts 19-20.)

## Verdict
Adopt rootId-digest namespace derivation plus validate-everything-then-CAS-delete mailbox draining for any file/mesh-backed out-of-process agent host; adapt digest slices and field sets to your protocol; omit authorship gating if your store is single-writer. Delivery path is direct-test-pinned end-to-end — no coverage caveat.
