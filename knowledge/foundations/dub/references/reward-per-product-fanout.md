<!-- capsule-v2 -->
# Per-product reward fan-out — when does one sale produce multiple ProductReward entries?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does the Stripe line-item integration decide to compute a reward PER PRODUCT instead of once per sale?

## productId-modifier gate & per-product loop
**Path/Symbol:** `apps/web/lib/partners/determine-partner-reward.ts:determinePartnerRewards` (:108-183).
**Signature:** `determinePartnerRewards({ event, programEnrollment, context?, amount, quantity }): ProductReward[]` where `ProductReward = { reward: RewardProps; sale: { amount, quantity } }`.
**Data Shape:** products come from `context.sale.products` (`{id, amount, quantity}[]`); modifiers re-parsed from `programEnrollment.saleReward?.modifiers`; note the plural function hardcodes `saleReward` — click/lead callers use the singular path.

### Decisive source
```ts
const hasProductIdModifier = modifiers.success
  ? modifiers.data.some((m) =>
      m.conditions.some(
        (c) => c.entity === "sale" && c.attribute === "productId",
      ),
    )
  : false;

// If there are products and a productId modifier,
// we need to calculate the reward for each product (for Stripe integration only)
if (products.length > 0 && hasProductIdModifier) {
```
(determine-partner-reward.ts :127-137)

**Flow:** parse saleReward modifiers → scan EVERY group and condition for an entity=sale/attribute=productId predicate → if products exist AND such a modifier exists, call `determinePartnerReward` once per product with context narrowed to that product's `{productId, amount}` → collect non-null results paired with the product's own amount+quantity → else single call carrying the caller's flat `amount`/`quantity`. A trailing `console.log("Reward context", ...)` (:180) precedes return.
**Invariant:** the per-product branch fires only on BOTH conditions — a productId modifier without line-items (non-Stripe providers) still takes the single-reward path with the order-total amount; per-product rewards can legitimately return fewer entries than products (null-filtered), so downstream commission creation must tolerate empty arrays.
**Probe:** deterministic probes (repo root): `grep -n 'hasProductIdModifier' apps/web/lib/partners/determine-partner-reward.ts` → :127 and :137; `grep -n '(c) => c.entity === "sale" && c.attribute === "productId"' apps/web/lib/partners/determine-partner-reward.ts` → :130; `grep -n 'console.log("Reward context"' apps/web/lib/partners/determine-partner-reward.ts` → :180. Direct tests: sale-reward.test.ts covers product scenarios (offline-blocked runner, standing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "determinePartnerRewards", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-gate (products AND productId-modifier) per-product fan-out with null-filtered collection. Adapt product shape. Omit the debug console.log.
