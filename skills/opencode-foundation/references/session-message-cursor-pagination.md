<!-- capsule-v2 -->
# Session message cursor pagination — how do you page an append-only message log backwards with opaque cursors, and make the next-page link survive proxies and CORS?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Given a session's messages stored in a DB table ordered by (time_created, id), how do you serve "the N most recent, then older pages" as an HTTP API where clients can follow `Link: rel="next"` from browser JS behind a reverse proxy?

## Opaque base64url cursor + limit+1 probe paging
**Path/Symbol:** `packages/opencode/src/session/message-v2.ts` (`Cursor` schema :63-66, `cursor.encode/decode` :71-81, `older` :95-97, `page` :425-466) + `packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts` (`messages` :106-146).
**Signature:** `page({sessionID, limit, before?}) → Effect<{items: WithParts[], more: boolean, cursor?: string}>`; `cursor.encode({id: MessageID, time: number}) → string` (base64url of JSON); handler query = `{limit?: int>=0, before?: string}` + workspace-routing fields.
**Data Shape:** cursor payload is exactly `{id, time}` — the tail row of the previous page; wire form is base64url(JSON) validated by Schema decode on the way in (invalid → 400). Response headers: `Link: <absolute-url>; rel="next"`, `X-Next-Cursor: <cursor>`, `Access-Control-Expose-Headers: Link, X-Next-Cursor`.

### Decisive source
```ts
// message-v2.ts:95 — tie-safe "strictly older" predicate for equal timestamps:
const older = (row: Cursor) =>
  or(lt(MessageTable.time_created, row.time), and(eq(MessageTable.time_created, row.time), lt(MessageTable.id, row.id)))
// message-v2.ts:425-466 — fetch limit+1, use the extra row only as a "more" probe:
  .orderBy(desc(MessageTable.time_created), desc(MessageTable.id))
  .limit(input.limit + 1)
...
  const more = rows.length > input.limit
  const slice = more ? rows.slice(0, input.limit) : rows
  const items = yield* hydrate(db, slice)
  items.reverse()                                   // DESC fetch → ASC response
  const tail = slice.at(-1)
  return { items, more, cursor: more && tail ? cursor.encode({ id: tail.id, time: tail.time_created }) : undefined }
// handlers/session.ts:110 — cursor pages must be bounded:
if (ctx.query.before && ctx.query.limit === undefined) return yield* new HttpApiError.BadRequest({})
// handlers/session.ts:133-142 — next link echoes the REAL origin:
// toURL() honors the Host + x-forwarded-proto headers, so the Link
// header echoes the real origin instead of a hard-coded localhost.
const url = Option.getOrElse(HttpServerRequest.toURL(request), () => new URL(request.url, "http://localhost"))
url.searchParams.set("limit", ctx.query.limit.toString())
url.searchParams.set("before", page.cursor)
```

**Flow:** request ⇒ if `before` present without `limit` → 400; decode+validate cursor (garbage → 400); requireSession (missing → 404); `page()` selects limit+1 rows DESC by (time_created, id) with the `older(cursor)` filter when paging; zero rows triggers a SessionTable existence probe so an empty-but-existing session returns `[]` while a missing session returns storage NotFoundError (→404) — "no messages" and "no session" stay distinguishable (:441-452); extra row discarded as the `more` flag; items reversed to chronological ascending; next cursor encodes the tail row. Handler then builds the absolute next URL via `HttpServerRequest.toURL(request)` (Host + x-forwarded-proto aware) and attaches Link/X-Next-Cursor/expose-headers.
**Invariant:** The cursor must be self-contained (id+time, no server-side session state) and tie-safe on identical timestamps (id breaks the tie). Pages are always returned oldest→newest even though the DB scan is newest-first. A client that follows `Link` must get a URL that works through its own proxy — never a hard-coded localhost.
**Probe:** `packages/opencode/test/server/httpapi-session.test.ts:956-971` ("serves paginated message link headers" pins `x-next-cursor` truthy, `link` containing `limit=1`, and `access-control-expose-headers` containing `x-next-cursor`); `:362-370` pins `before` without `limit` → 400 and `before=invalid` → 400; source pin:
```bash
grep -n 'limit(input.limit + 1)' packages/opencode/src/session/message-v2.ts
grep -n 'Access-Control-Expose-Headers' packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "MessageV2 page cursor encode older X-Next-Cursor Link rel next", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the limit+1-probe backward paging with a self-contained (id, time) cursor and the tie-safe `older` predicate; adopt rebuilding the next-link from the incoming request's Host/x-forwarded-proto plus explicit CORS exposure of both headers. Adapt the cursor encoding (any opaque validated token works) and the empty-session existence probe to your store; omit opencode's specific WithParts hydration shape. Direct tests read whole; bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
