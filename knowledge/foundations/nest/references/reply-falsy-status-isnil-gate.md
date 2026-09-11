<!-- capsule-v2 -->
# reply() falsy-status gate — why must a porting adapter forward statusCode 0/NaN instead of dropping it?

**Source:** nest MIT `master@4c38a5ab1` (fix commit e03cf5c86 "apply falsy status codes"); Codebase Memory project `nest`. **Question:** When the framework hands an adapter `reply(response, body, statusCode?)`, which values must trigger `response.status(...)` and which must be skipped?

## Falsy-status forwarding across both HTTP adapters
**Path/Symbol:** `packages/platform-express/adapters/express-adapter.ts:108-137 ExpressAdapter.reply` and `packages/platform-fastify/adapters/fastify-adapter.ts:438-496 FastifyAdapter.reply`.
**Signature:** `reply(response: any /* TRawResponse | TReply */, body: any, statusCode?: number)`.
**Data Shape:** `statusCode?: number` may be legitimately falsy-but-present (`0`, `NaN`) — the ONLY skippable values are `undefined`/`null`. `body` may be nil, a `StreamableFile`, an object, or a primitive.

### Decisive source
```ts
// express-adapter.ts:109 (fastify twin: :459) — was `if (statusCode)` before e03cf5c86
if (!isNil(statusCode)) {
  response.status(statusCode);
}
if (isNil(body)) {
  return response.send();
}
```

**Flow:** (1) `!isNil(statusCode)` gate forwards even `0`/`NaN` to the host framework, which rejects invalid statuses itself; (2) nil body ⇒ bare `send()`; (3) `StreamableFile` ⇒ stream headers applied only-if-absent, `error`→`body.errorHandler`, pipe into response; (4) non-JSON `Content-Type` already on the response AND `body?.statusCode >= HttpStatus.BAD_REQUEST` ⇒ warn ("you might need a custom ExceptionFilter") and force `application/json`; (5) object ⇒ `json(body)`, else `send(String(body))`. The fastify variant synthesizes a real `Reply` when handed the RAW response — detected by `isNativeResponse`: `!('status' in response)` (:805-809) — constructing `new Reply(response, { [kRouteContext]: { preSerialization: null, preValidation: [], preHandler: [], onSend: [], onError: [] } }, {})` (:443-457) so `.status/.header/.send` exist outside the normal request pipeline.
**Invariant:** Presence is tested with `isNil`, never truthiness. Dropping falsy codes leaves the pre-handler status (200/201) on the wire with an error body — the silent-success bug class this gate exists to kill. A porter who "simplifies" `!isNil(x)` back to `if (x)` reintroduces it.
**Probe:** `packages/platform-express/test/adapters/express-adapter.spec.ts:76-88` ("should apply falsy status codes instead of dropping them" loops `[0, NaN]` and asserts `response.status` called WITH the value); fastify twin `packages/platform-fastify/test/adapters/fastify-adapter.spec.ts:38-50`; omission cases :68-74/:30-36 assert NO call when arg absent.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "reply apply falsy status codes isNil adapter", limit: 10 });
```

## Verdict
Adopt the `!isNil` presence gate and the nil-body/stream/content-type-mismatch ladder verbatim; adapt the fastify synthetic-Reply construction to your host's reply shape (the `kRouteContext` hook arrays are fastify-internals you must stub equivalently); omit express's Logger instance vs fastify's static `Logger.warn(name)` difference (cosmetic). Coverage caveat: runner blocked (no node_modules in cron env) — spec titles/loops pinned by line, not executed.
