<!-- capsule-v2 -->
# RouteParamsFactory.exchangeKeyForValue — how raw adapter requests become typed handler arguments

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What does each route-argument kind extract from the adapter request, and which cases fall back to whole-object vs property access?

## exchangeKeyForValue
**Path/Symbol:** `packages/core/router/route-params-factory.ts:exchangeKeyForValue` (:5-46).
**Signature:** `exchangeKeyForValue<TRequest, TResponse, TResult>(key: RouteParamtypes | string, data: string, { req, res, next }): TResult | null`.
**Data Shape:** `data` = the `@Query('x')` selector (undefined ⇒ whole object); request fields are the adapter-normalized Express-ish surface (`req.body/params/query/headers/session/rawBody/ip/hosts/files`).

### Decisive source
```ts
case RouteParamtypes.BODY:  return data && req.body ? req.body[data] : req.body;
case RouteParamtypes.PARAM: return data ? req.params[data] : req.params;
case RouteParamtypes.QUERY: return data ? req.query[data] : req.query;
case RouteParamtypes.HEADERS: return data ? req.headers[data.toLowerCase()] : req.headers; // lowercased!
case RouteParamtypes.HOST:  const hosts = req.hosts || {}; return data ? hosts[data] : hosts;
case RouteParamtypes.NEXT:  return next as any;
case RouteParamtypes.REQUEST: return req;      case RESPONSE: return res;
case RouteParamtypes.RAW_BODY: return req.rawBody;   case SESSION: return req.session;
case RouteParamtypes.FILE:  return req[data || 'file'];   case FILES: return req.files;
case RouteParamtypes.IP:    return req.ip;
default: return null;                            // unknown kinds → null, never throw
```

**Flow:** per decorated parameter at request time → switch on internal enum → property-or-whole extraction → value flows into the PipesConsumer chain.
**Invariant:** (1) BODY guards `data && req.body` — a missing body with a data selector yields undefined rather than TypeError; PARAM/QUERY lack that guard because params/query objects always exist on the normalized request. (2) Headers are CASE-INSENSITIVE by lowercasing the selector (adapter stores headers lowercased) — selectors must be lowercase or lookup silently misses. (3) FILE uses `req[data || 'file']` — the decorator's field name selects between multer's `file` and `files` conventions. (4) Unknown keys return null (custom factories handled upstream via getCustomFactory), keeping this table total.
**Probe:** `packages/core/test/router/route-params-factory.spec.ts::exchangeKeyForValue` (per-kind extraction matrix incl. header casing).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouteParamsFactory exchangeKeyForValue req.body req.headers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the single extraction table between your HTTP adapter and handler arguments; adapt the request surface to your framework; omit exotic kinds (session/file/ip) you don't support but keep default-null totality. Porting wrong: skipping the body-existence guard (crashes on empty POSTs) or case-sensitive header lookups.
