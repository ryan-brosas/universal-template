<!-- capsule-v2 -->
# Hub discovery record — how do clients find a local daemon without racing stale or half-written records?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What is the durable file contract for publishing, reading, and deleting a "who is running" daemon record so concurrent clients never see torn writes or delete someone else's record?

## Schema-gated read, atomic publish, ownership-scoped clear
**Path/Symbol:** `sdk/packages/core/src/hub/discovery/index.ts:346-461` (`readHubDiscovery`, `writeHubDiscovery`, `clearHubDiscoveryIfOwned`; mutation lock at 524-533).
**Signature:** `readHubDiscovery(discoveryPath) → Promise<HubServerDiscoveryRecord | undefined>`; `writeHubDiscovery(discoveryPath, record) → Promise<void>`; `clearHubDiscoveryIfOwned(discoveryPath, hubId) → Promise<boolean>`.
**Data Shape:** Record = `{hubId, protocolVersion, authToken, host, port, url, startedAt, updatedAt}` required strings/number; optional `min/maxClientProtocolVersion, capabilities[], coreVersion, buildId, buildEpochMs, pid`. Any malformation ⇒ read returns `undefined`, never throws.

### Decisive source
```ts
// READ: every required field is type-checked; anything odd => undefined
if (
    typeof parsed.hubId !== "string" ||
    typeof parsed.protocolVersion !== "string" ||
    typeof parsed.authToken !== "string" ||
    ...
) { return undefined; }
// WRITE: temp file => fsync => atomic same-dir rename => best-effort dir fsync
temporaryFile = await open(temporaryPath, "wx", 0o600);
...
await temporaryFile.sync();
// On local filesystems with atomic same-directory rename semantics, this
// prevents readers from observing the old remove/write gap ...
await rename(temporaryPath, discoveryPath);
// CLEAR: inside the SAME mutation lock, only if we still own the record
const current = await readHubDiscovery(discoveryPath);
if (current?.hubId !== hubId) { return false; }
await rm(discoveryPath, { force: true });
```

**Flow:** write takes `<path>.mutation` mkdir-lock → mkdir parent → open unique temp `(wx, 0o600)` → write JSON+\n → fsync file → close → **rename over target** → try dir fsync (Windows/virtual FS reject opening directories; durability degrades, atomicity does not) → on any error rm temp and rethrow. Read parses defensively and rebuilds the record field-by-field with per-field type filters (capabilities filtered to strings). Clear re-reads under the lock and deletes only when `current.hubId === hubId`.
**Invariant:** Readers never observe a partial record (temp+rename publication); a retiring hub can never delete a successor's record (ownership check inside the same lock that serializes both); malformed input degrades to "no hub found", not an exception path.
**Probe:** `grep -cF 'await rename(temporaryPath, discoveryPath);' sdk/packages/core/src/hub/discovery/index.ts` → 1; `grep -cF 'if (current?.hubId !== hubId) {' ...` → 1; `grep -cF 'typeof parsed.hubId !== \"string\" ||' ...` → 1. Direct tests: `sdk/packages/core/src/hub/discovery/index.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "readHubDiscovery writeHubDiscovery atomic rename", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt schema-gated defensive reads, wx-temp + fsync + same-dir-rename publication, and ownership-checked deletes under one serialization point. Adapt record fields to host vocabulary and the fsync ladder to platform support. Omit Cline's hub-specific auth/pid semantics. Runner-BLOCKED here (no node_modules); probe battery executed green.
