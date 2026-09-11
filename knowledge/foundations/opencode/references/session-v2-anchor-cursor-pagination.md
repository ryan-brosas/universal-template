<!-- capsule-v2 -->
# Session v2 anchor cursor pagination — how do you paginate an ordered list in BOTH directions with opaque cursors that survive query changes?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** `/api/session` and `/api/session/:id/message` must page forward AND backward through an ordered list, with cursors that are safe to store in a client, immune to the user changing filters mid-pagination, and still decodable after schema evolution. How is that built?

## Cursor = base64url JSON embedding the full query context + anchor
**Path/Symbol:** `packages/protocol/src/groups/session.ts` (`withCursor` :49-53, `SessionsCursorInput` :55-59, `SessionsCursor` make/parse :65-84) + `packages/server/src/handlers/session.ts` (`session.list` :22-58) + `packages/server/src/handlers/message.ts` (`Cursor` :10-14, conflict gate :35-36, decode :37-39, encode :74-75) + `packages/core/src/session.ts` (`list` order flip :233-270, anchor predicate :255-264, reverse :302; `messages` seq anchor :308-336) + `packages/schema/src/session.ts` (`ListAnchor` :46-50).
**Signature:** `SessionsCursor = branded string`; `make(input) → base64url(JSON(input))`; `parse(s) → Effect<{...query fields, anchor: ListAnchor}, "Invalid cursor">`; message `Cursor = {id, order: "asc"|"desc", direction: "previous"|"next"}`.
**Data Shape:** session-list cursor JSON embeds directory/project/subpath/workspace/order/search (whatever the page was queried with) plus `anchor: {id, time: Finite, direction}`; message cursor JSON is just `{id, order, direction}` — no time, because the engine resolves the anchor's durable `seq` from the id at query time.

### Decisive source
```ts
// protocol/src/groups/session.ts:49-53 — the cursor REPLACES limit with an anchor, keeps every other field:
const withCursor = <Fields extends Schema.Struct.Fields>(schema: Schema.Struct<Fields>) =>
  schema.mapFields((fields) => ({
    ...Struct.omit(fields, ["limit"]),
    anchor: Session.ListAnchor,
  }))

// core/session.ts:271 + :255-264 — direction flips the requested order; tie-safe on id:
const order = direction === "previous" ? (requestedOrder === "asc" ? "desc" : "asc") : requestedOrder
// asc: or(gt(time, t), and(eq(time, t), gt(id, anchor.id)))   desc: mirrored with lt
// ...rows fetched in `order`, then:
return (direction === "previous" ? rows.toReversed() : rows).map((row) => fromRow(row))

// server/src/handlers/message.ts:35-36 — order is INSIDE the cursor, so combining is ambiguous:
if (ctx.query.cursor && ctx.query.order !== undefined)
  return yield* new InvalidCursorError({ message: "Cursor cannot be combined with order" })
```

**Flow:** A page response builds `cursor.previous` from the FIRST row and `cursor.next` from the LAST row, each re-embedding the page's own query context with a fresh anchor (`handlers/session.ts:38-56`, `handlers/message.ts:74-75`). On the next request the handler parses the cursor (any decode failure → 400 `InvalidCursorError{message:"Invalid cursor"}`) and uses its embedded fields INSTEAD of the raw query — so a client can keep paging even if it stops sending the original filters. The engine then flips the SQL order when direction is "previous" (fetch desc, return asc) and applies the anchor predicate `(time > t) OR (time = t AND id > id)` (mirrored for desc) — the id tiebreak makes identical timestamps page-safe. For messages the anchor resolves to the durable aggregate `seq` (`gt/lt(SessionMessageTable.seq, anchor.seq)`); an unknown anchor id yields an EMPTY page, not an error (:319). Schema evolution is tolerated by construction: `Schema.Struct` decoding ignores excess properties, so legacy message cursors carrying an old `time` field still decode (test pins this explicitly).
**Invariant:** A cursor is self-sufficient: it carries everything needed to reproduce the page's ordering and scope, which is why `cursor` + `order` together is a 400 (two sources of truth for one decision). Response rows always read in the client's requested order regardless of direction; the fetch order may differ. Forward/backward paging from the same cursor must converge on the same rows — the id tiebreak is what guarantees that under duplicate timestamps.
**Probe:** `packages/opencode/test/server/httpapi-session.test.ts:431-520` ("returns v2 public request errors for cursor and workspace query failures" pins: base64url-decoded session cursor equals `{order:"asc", directory, search:"v2", anchor:{id, direction:"next"}}`; next page 200; `cursor=invalid` → 400 `{_tag:"InvalidCursorError", message:"Invalid cursor"}`; `workspace=bad` → 400 `InvalidRequestError{kind:"Query"}`; message cursor JSON exactly `{id, order:"desc", direction:"next"}`; second page returns the remaining message; a LEGACY cursor with extra `time` field still pages correctly; `cursor`+`order=asc` → 400 "Cursor cannot be combined with order"); source pin:
```bash
grep -n 'Struct.omit(fields, \["limit"\])' packages/protocol/src/groups/session.ts
grep -n 'Cursor cannot be combined with order' packages/server/src/handlers/message.ts
grep -n 'direction === "previous" ? rows.toReversed()' packages/core/src/session.ts
```
expect 1 + 1 + 2 hits (list and messages both reverse).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionsCursor withCursor ListAnchor InvalidCursorError cursor previous next", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt context-embedding opaque cursors for bidirectional pagination: the cursor carries the page's own query scope + ordering + anchor, the handler prefers cursor fields over raw query fields, and conflicting explicit params are a typed 400 rather than a guess. Adopt the flip-fetch-then-reverse pattern (fetch in the direction that makes the anchor predicate a simple comparison, return in the requested order) and the (time, id) tie-safe predicate for any table without a unique sequence; use the durable-seq anchor where one exists and treat unknown anchors as empty pages. Adapt the excess-property-tolerant decode for your own cursor evolution needs; omit the session-list vs message-cursor asymmetry if both of your tables share one ordering column. Direct test read whole (httpapi-session.test.ts 1090L, pass 7); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
