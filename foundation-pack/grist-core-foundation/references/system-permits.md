<!-- capsule-v2 -->
# Permits — how does a server initiate work that normally only a user is allowed to do?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you grant short-lived, scoped, unguessable authorization to background/system actors without weakening the normal auth path?

## TTL'd secret-keyed capability documents in a pluggable store
**Path/Symbol:** `app/server/lib/Permit.ts:Permit/IPermitStore` (whole file, 70L); redis impl `app/gen-server/lib/DocWorkerMap.ts:getPermitStore` (511–538); in-memory impl `DummyDocWorkerMap.getPermitStore` (86–116); consumption `app/server/lib/Authorizer.ts` + `FlexServer.ts` (`setPermit({docId})` :959, :2792).
**Signature:** `setPermit(permit: Permit, ttlMs?: number): Promise<string>`; `getPermit(key): Promise<Permit | null>`; `removePermit(key)`.
**Data Shape:** `Permit = { docId?, workspaceId?, org?, otherDocId?, sessionId?, url?, action? }`; key format ``permit-${prefix}-${uuidv4()}``; default TTL 60s (redis SETEX, integer seconds); store selected per prefix via `getPermitStore(prefix, defaultTtlMs)`.

### Decisive source
```ts
// Permits are stored in redis ... as json, in keys that expire within minutes.
// The keys should be effectively unguessable.                        (Permit.ts header)
async setPermit(permit: Permit, ttlMs?: number): Promise<string> {
  const key = formatPermitKey(uuidv4(), prefix);          // permit-<prefix>-<uuid>
  await client.setexAsync(key, Math.ceil(duration / 1000.0), JSON.stringify(permit));
  return key;
},
async getPermit(key: string): Promise<Permit | null> {
  if (!checkPermitKey(key, prefix)) { throw new Error("permit could not be read"); }
  const result = await client.getAsync(key);
  return result && JSON.parse(result);
},
```

**Flow:** system code prepares a minimal Permit (only the ids the task touches — e.g. trash deletion sets `docId`) → stores it → gets an unguessable expiring key → calls the INTERNAL API carrying `Permit: <key>` header → the authorizer, seeing a valid unexpired permit for exactly that resource/action, bypasses the user-permission ladder for that one request → optional early `removePermit`. Expiry does the cleanup; keys never outlive the need by more than minutes. Prefix-scoped stores keep different subsystems' permits namespaced and independently TTL-tuned (e.g. SAML login state uses `waitMinutes * 60 * 1000`, assistant state 1 hour).
**Invariant:** a permit authorizes ONLY what its JSON fields name — no wildcard grants; the key check enforces prefix match so one subsystem's key can't be replayed against another's endpoint; permits are single-resource and short-lived by construction, so leakage has a ≤TTL blast radius; absence/expiry yields null and the request falls through to normal (failing) authorization rather than erroring open.
**Probe:** exercised across API suites rather than a dedicated file (coverage caveat): `test/server/lib/docapi/` doc-deletion flows use internal permits; direct interface consumers verified at `Authorizer.ts`/`FlexServer.ts` call sites; in-memory twin behavior pinned by `test/server/lib/Authorizer.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "IPermitStore setPermit getPermit", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the pattern for machine-initiated privileged actions (cron cleanups, cross-service callbacks, OAuth-state carry): capability = minimal JSON scope + unguessable expiring key + prefix isolation, read-through-null on miss. Adapt storage (any TTL KV), key format, and scope vocabulary to host. Omit the two-document (`otherDocId`) case unless you have fork/merge flows like grist's.
