<!-- capsule-v2 -->
# Race-safe get-or-create funnel — why does Prisma upsert still throw P2002 on MySQL, and what is the documented fallback?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Every conversion rail (track routes, Stripe/AppsFlyer/HubSpot/Singular webhooks, lead actions) must resolve-or-create the SAME customer identity concurrently — what one kernel do they share?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/api/customers/get-or-create-customer.ts:getOrCreateCustomer` (:13-74).
**Signature:** `getOrCreateCustomer({ where: CustomerWhereUniqueInput | CustomerWhereInput, create: CustomerUncheckedCreateInput, findMode?: "first" | "unique" = "unique" }) => { customer, created }`.
**Data Shape:** `findMode` chosen per caller key shape: `"unique"` for compound-unique lookups (externalId), `"first"` for non-unique predicates. Result carries an explicit `created` boolean so callers can branch side effects.

### Decisive source
```ts
/**
 * Prisma's `customer.upsert()` can still throw P2002 under MySQL concurrency
 * (two requests miss the row, both attempt insert). This helper finds first,
 * creates if missing, and on unique-constraint conflict falls back to find
 * using `where`, so concurrent track-lead / track-sale / etc. share one path
 * instead of failing the request.
 */                                    // :4-12 — the WHY lives in the docstring
const customer = findMode === "first"
  ? await prisma.customer.findFirst({ where })
  : await prisma.customer.findUnique({ where });
if (customer) return { customer, created: false };
try {
  return { customer: await prisma.customer.create({ data: create }), created: true };
} catch (error) {
  if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
    const customer = findMode === "first"
      ? await prisma.customer.findFirstOrThrow({ where })
      : await prisma.customer.findUniqueOrThrow({ where });
    return { customer, created: false };          // loser of the race adopts the winner's row
  }
  throw error;
}
```

**Flow:** find → miss ⇒ create → P2002 (concurrent insert won) ⇒ re-find with the SAME predicate via *OrThrow → return with created:false. Any other error propagates.
**Invariant:** Duplicate concurrent identity creation converges on ONE row instead of failing a conversion; the kernel never retries blindly and never swallows non-P2002 errors. This is THE identity funnel for every rail: depth-2 inbound trace = 19 callers (5 direct: checkoutSessionCompleted, attributeViaPromotionCodeId, syncCustomer, trackLead, trackSale; hop-2: the four /track/* route twins, stripe webhook route + subscription-created + invoice-paid, appsflyer webhook, hubspot ×2, singular ×2, submitted-leads qualify/closed-won ×2) — executed live this run.
**Probe:** Direct test `tests/tracks/track-lead.test.ts` :67-86 — integration harness (PG+Redis+QStash cloud-gated; offline here): duplicate `/track/lead` with the same customerExternalId returns the SAME customer ("should return the same response since it's idempotent" :80).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getOrCreateCustomer race safe upsert P2002", limit: 5 }); // rank-1 :13-74
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getOrCreateCustomer", direction: "inbound", depth: 2 }); // callers_total=19
```

## Verdict
Adopt find→create→catch-P2002→re-find as the standard get-or-create under MySQL-family databases, keeping the docstring that explains WHY upsert alone is insufficient. Adapt findMode to your unique-index layout. Omit the created-flag at your peril — attribution webhooks key first-time-vs-returning behavior off it.
