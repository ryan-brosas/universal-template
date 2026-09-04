<!-- capsule-v2 -->
# First-conversion heuristic — when is a sale "the customer's first" for reward eligibility?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** How do you decide first-conversion status from denormalized customer counters without a per-customer query, and what false positives do you accept?

## Two-line predicate with a documented TODO
**Path/Symbol:** `apps/web/lib/analytics/is-first-conversion.ts:isFirstConversion` (:3-:23).
**Signature:** `({customer}: {customer: Pick<Customer,"sales"|"linkId">; linkId?: string}) => boolean`.
**Data Shape:** reads ONLY two denormalized columns on Customer (`sales` counter, `linkId` = original referral link) plus the current event's linkId — no Commission lookup.

### Decisive source
```ts
if (customer.sales === 0) return true;
if (customer.linkId !== linkId) {
  // TODO: fix edge case where customer was brought in by a different link,
  // but then had recurring sales on the current link
  return true;
}
return false;
```

**Flow:** zero recorded sales ⇒ first conversion (the common case, checked first) ⇒ else if the selling link differs from the customer's original referral link ⇒ STILL treated as first conversion on THIS link ⇒ same-link repeat ⇒ not first.
**Invariant:** the predicate deliberately prefers FALSE POSITIVES for cross-link sales: a customer acquired by link A then buying via link B grants B's partner a first-conversion reward even though the customer has purchased before. The comment marks this as known and accepted. Callers therefore cannot rely on it as an accounting truth — only as a reward-eligibility heuristic.
**Probe:** no direct unit test at pin (coverage caveat). Anchors observed live: `customer.sales === 0` :11, `customer.linkId !== linkId` :17.

## Caller family: every commission-creation entry point
**Path/Symbol:** graph inbound trace of `isFirstConversion` — callers_total 13.
**Flow:** `_trackSale` / `checkoutSessionCompleted` / `invoicePaid` (Stripe), `createCommissionFromPS`, `createShopifySale`, `createNetworkReferralCommission`, `resolveLinkAndCustomer`, generic `createCommission`, scripts/templates — i.e., EVERY rail that mints a Commission funnels through this one predicate before consulting the reward/commission-eligibility ladders (see commission-eligibility-ladder capsule).
**Invariant:** single source of truth for "first": adding a new sale-intake rail must reuse the predicate rather than re-derive the condition, or first-conversion rewards silently diverge between rails.
**Probe:** retrieval executed live: `trace_path {project:"dub", function_name:"isFirstConversion", direction:"inbound", depth:1}` → 13 callers listed above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "isFirstConversion", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "dub", qualified_name: "dub.apps.web.lib.analytics.is-first-conversion.isFirstConversion", include_neighbors: true });
```

## Verdict
Adopt: counter-based first-sale check + cross-link-is-also-first policy with the trade-off written into the code. Adapt which counter/fields your customer row carries; omit dub's specific Customer schema. If your rewards are money-accurate requirements, do NOT adopt the cross-link branch blindly — it over-pays by design. Coverage caveat: no direct unit test at pin; contract pinned by source read + 13-caller trace.
