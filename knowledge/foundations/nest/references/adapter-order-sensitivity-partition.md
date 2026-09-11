<!-- capsule-v2 -->
# adapter order-sensitivity partition — why does the same boolean gate specificity sorting AND duplicate-rejection policy?

**Source:** nest MIT `master@4c38a5ab1`; Codebase Memory project `nest`. **Question:** How must a ported router decide whether to sort routes by specificity and how it may treat duplicate registrations — and why is one flag carrying both decisions?

## Express true / Fastify false, defaulted true for unknown adapters
**Path/Symbol:** `packages/platform-express/adapters/express-adapter.ts:385-387 isRouteOrderSensitive` (returns `true`), `packages/platform-fastify/adapters/fastify-adapter.ts:761-763` (returns `false`); consumer `packages/core/nest-application.ts:219-226`.
**Signature:** `isRouteOrderSensitive(): boolean` on `AbstractHttpAdapter`.
**Data Shape:** No args; pure capability predicate. Abstract base declares no default — the consumer supplies one.

### Decisive source
```ts
// nest-application.ts:219-226
const adapterIsOrderSensitive =
  this.httpAdapter.isRouteOrderSensitive?.() ?? true;
const shouldSortBySpecificity =
  resolutionStrategy === 'specificity' && adapterIsOrderSensitive;
// Adapters that are not order-sensitive (e.g. Fastify) currently
// also reject duplicate (method, URL) registrations synchronously
// from the underlying router. Treat the two properties as one
// signal until a separate capability flag is introduced.
const adapterRejectsDuplicates = !adapterIsOrderSensitive;
```

**Flow:** Registration-time branch: conflict-policy or specificity-sort configured AND adapter order-insensitive ⇒ routes are collected/deferred (see route-registration-layering) so detection/sorting runs BEFORE the adapter sees any route. Order-sensitive adapters keep insertion-order semantics (registration sequence IS match priority). The in-source comment makes the coupling explicit: find-my-way (fastify's router) rejects duplicate (method, URL) synchronously, express's router silently shadows — one capability bit currently models both.
**Invariant:** An unknown adapter MUST default to order-sensitive (`?? true`) — the conservative choice that keeps specificity sorting enabled and never assumes synchronous duplicate rejection. Never split this into two flags without introducing a separate capability query: the comment pins them as deliberately conflated.
**Probe:** `grep -n "isRouteOrderSensitive" packages/core/nest-application.ts` resolves exactly ONE site (:219 — the in-source comment below uses prose "order-sensitive", never the symbol); `packages/platform-fastify/adapters/fastify-adapter.ts:761-763` contains exactly one `return false`. Direct test coverage caveat: no spec instantiates this predicate — behavior pinned by consumer wiring + both adapter returns.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"nest","query":"isRouteOrderSensitive adapter order sensitive duplicate rejection","limit":5}'
```

## Verdict
Adopt the tri-state decision table (sort+defer vs insert-order) and the conservative default; adapt the duplicate-rejection conflation to your router (if your host neither sorts nor rejects duplicates, both flags need re-adjudication); omit fastify's find-my-way specifics. Coverage caveat: deterministic probes only (runner blocked).
