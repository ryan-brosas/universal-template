<!-- capsule-v2 -->
# Credential store — how do you keep exactly one usable credential per integration with replace-on-create semantics?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Integrations (providers, gateways) need at most one active credential each, but users re-authenticate often. How do you store credentials so "create" atomically replaces the previous credential for the same integration, while reads tolerate corrupt or legacy rows?

## Replace-on-create in one transaction
**Path/Symbol:** `packages/core/src/credential.ts` (`create` :94-121, `stored` :56-64, `all`/`list` :66-82, `node` :138).
**Signature:** `create({integrationID, value, label?}) → Effect<Info>`; `list(integrationID) → Effect<Info[]>`; `Value = Credential.Value` (Key | OAuth tagged union, Schema-decoded).
**Data Shape:** `Info = { id, integrationID, label, value }` persisted in CredentialTable (`integration_id`, `label`, `value` JSON); label defaults to "default".

### Decisive source
```ts
// credential.ts:102-118 — delete-then-insert inside one transaction = replace semantics
yield* db.transaction((tx) =>
  Effect.gen(function* () {
    yield* tx
      .delete(CredentialTable)
      .where(eq(CredentialTable.integration_id, credential.integrationID))
      .run()
    yield* tx.insert(CredentialTable).values({
      id: credential.id,
      integration_id: credential.integrationID,
      label: credential.label,
      value: credential.value,
    }).run()
  }),
).pipe(Effect.orDie)
```

**Flow:** create builds a fresh ID, then in ONE transaction deletes every row for the integration and inserts the new one — the invariant "at most one credential per integration" holds without an upsert and without a read-modify-write race. Reads decode `value` with `Schema.decodeUnknownSync` and SILENTLY DROP rows that fail decode or lack integration_id (stored() returns undefined → flatMap filters), so a corrupt or legacy row degrades to "credential absent" instead of failing every read. All DB failures are orDie (infrastructure defects, not typed errors). update() no-ops when neither label nor value is provided. The node is a GLOBAL node (makeGlobalNode), not location-scoped — credentials are machine-wide.
**Invariant:** one credential per integration, maintained by transactional replace; corrupt rows vanish on read rather than poisoning the list; the catalog's availability predicate (see catalog-availability-projection) reads this table through Integration connections, so replace-on-create immediately changes model availability.
**Probe:** `packages/core/test/credential.test.ts` (36L, 1 `it.effect`): "stores, updates, lists, and removes credentials" pins the full lifecycle — create → list returns exactly it; label update visible; a SECOND create for the same integration REPLACES (list equals only the replacement); remove empties the list. Cross-file pin: `packages/core/test/catalog.test.ts` "derives availability from active credentials without changing provider state" creates two credentials sequentially and pins availability staying true with stored body untouched. Source pin:
```bash
grep -c 'transaction' packages/core/src/credential.ts   # expect 1
grep -c 'orDie' packages/core/src/credential.ts        # expect 7
grep -c 'makeGlobalNode' packages/core/src/credential.ts # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Credential create transaction delete integration_id replace decodeUnknownSync stored global node", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt transactional delete-then-insert replace-on-create for one-credential-per-integration and the decode-tolerant read (corrupt rows drop silently). Adapt the storage backend and the Value union to your host; omit the specific schema package. Coverage caveat: single direct test (36L) covers the lifecycle but not the corrupt-row read path — that branch is source-confirmed only; Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
