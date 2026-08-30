<!-- capsule-v2 -->
# API result pruning — how do you strip internal DB fields from every JSON response in one place?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you guarantee entity fields like apiKey/stripe ids/userId NEVER cross the API boundary, including nested objects, without per-endpoint discipline?

## One JSON.stringify replacer over the whole reply tree + denylist-by-default sendReply funnel
**Path/Symbol:** `app/server/lib/requestUtils.ts`: `INTERNAL_FIELDS` denyset (45–49), `pruneAPIResult` (298–318), `sendReply` (261–287), `sendOkReply` (289–296), `SendReplyOptions.allowedFields` (254–256); twin apply-through `pruneConfigAPIResult` pick-list in `attachEarlyEndpoints.ts` (399–416).
**Signature:** `pruneAPIResult<T>(data: T, allowedFields?: Set<string>): T | undefined`; `sendReply(req: Request | null, res, result: QueryResult<T>, options?)`.
**Data Shape:** `INTERNAL_FIELDS` = { apiKey, billingAccountId, firstLoginAt, lastConnectionAt, filteredOut, ownerId, gracePeriodStart, stripeCustomerId, stripeSubscriptionId, stripeProductId, userId, isFirstTimeUser, allowGoogleLogin, authSubject, usage, createdBy, unsubscribeKey }.

### Decisive source
```ts
const output = JSON.stringify(data,
  (key: string, value: any) => {
    if (key === "removedAt" && value === null) { return undefined; }
    if (key === "disabledAt" && value === null) { return undefined; }
    if (key === "options" && value === null)   { return undefined; }
    if (allowedFields?.has(key)) { return value; }
    if (key === "connectId" && value === null) { return undefined; }
    return INTERNAL_FIELDS.has(key) ? undefined : value;
  });
return output !== undefined ? JSON.parse(output) : undefined;
// sendReply: 2xx => res.json(data ?? null)   // "can't handle undefined"
//      else => res.json({ error: result.errMessage })
```

**Flow:** every homedb route returns a `QueryResult` → `sendReply` prunes THEN sets status THEN serializes; non-2xx collapses to `{error}` shape so internals of failures don't leak either. The replacer recurses into EVERY nested key (JSON.stringify walks the whole tree), so an org containing workspaces containing docs is pruned at all depths. Null-suppression keys (removedAt/disabledAt/options/connectId) keep responses clean rather than leaking state shape. `allowedFields` is the explicit escape hatch for fields that are safe in context.
**Invariant:** pruning happens in exactly ONE funnel — new endpoints must route through sendReply or replicate the replacer (the config endpoints use a positive pick-list instead because Config rows have few fields). `req: Request | null` first arg doubles as the logging switch: pass null to log nothing about the request. Round-trip cost accepted (~15µs/kB) — do not micro-optimize into a recursive walker that misses keys stringify would catch.
**Probe:** exercised on every homedb API suite (`test/gen-server/*` assert response bodies exclude INTERNAL_FIELDS); direct unit coverage absent at this pin — recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "sendReply pruneAPIResult INTERNAL_FIELDS allowedFields", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stringify-replacer prune as a defense-in-depth layer under explicit DTO whitelists — it catches the field someone added to the entity last week. Adapt the denylist contents to your schema; prefer converting to allowlist pick-lists (as attachEarlyEndpoints does) where response shapes are small and stable. Omit the null-suppression cosmetics if your clients tolerate explicit nulls.
