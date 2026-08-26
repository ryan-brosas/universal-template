<!-- capsule-v2 -->
# Group reward surface helpers — event-ordered reward sorting and the null-safe group triple

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** In what canonical order are a group's rewards presented, and how is the (click, sale, lead, discount) bundle normalized?

## sortRewardsByEventOrder + getGroupRewardsAndDiscount
**Path/Symbol:** `apps/web/lib/partners/sort-rewards-by-event-order.ts:sortRewardsByEventOrder` (:10-31); `apps/web/lib/partners/get-group-rewards-and-discount.ts:getGroupRewardsAndDiscount` (:4-18).
**Signature:** `sortRewardsByEventOrder<T extends Pick<Reward,"event">>(rewards: T[], customEventOrder?): T[]`; `getGroupRewardsAndDiscount({clickReward, saleReward, leadReward, discount}): {rewards: RewardProps[], discount: RewardProps|null}`.
**Data Shape:** default order `[click, lead, sale, referral]`; unknown events sort LAST via MAX_SAFE_INTEGER; input array never mutated.

### Decisive source
```ts
const sortedRewards = [...rewards];

sortedRewards.sort((a, b) => {
  const aIndex = eventOrderMap.get(a.event) ?? Number.MAX_SAFE_INTEGER;
  const bIndex = eventOrderMap.get(b.event) ?? Number.MAX_SAFE_INTEGER;

  return aIndex - bIndex;
});

return sortedRewards;
```
(sort-rewards-by-event-order.ts :21-30)

**Flow:** sorter builds an event→rank Map from default or custom order → spread-copies the input (no caller mutation) → stable sort by rank with unseen events pinned to Number.MAX_SAFE_INTEGER (preserving relative order among themselves and after all known events). The group helper filters null rewards from the fixed [clickReward, saleReward, leadReward] triple and coalesces `discount ?? null` — the single read-shape every program-settings UI consumes.
**Invariant:** JS Array.sort is stable (ES2019+) so equal-rank entries keep input order — but unknown-event pinning means a customOrder that omits an event silently demotes it below ALL known events rather than throwing; the copy-before-sort protects callers iterating the original array concurrently.
**Probe:** deterministic probes (repo root): `grep -n 'DEFAULT_REWARD_EVENT_ORDER' apps/web/lib/partners/sort-rewards-by-event-order.ts` → :3/:12/:15; `grep -c 'MAX_SAFE_INTEGER' apps/web/lib/partners/sort-rewards-by-event-order.ts` → 2 (:24/:25); `grep -n 'sortedRewards = \[...rewards\]' apps/web/lib/partners/sort-rewards-by-event-order.ts` → :21; `grep -n 'discount ?? null' apps/web/lib/partners/get-group-rewards-and-discount.ts` → :16.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "sortRewardsByEventOrder", limit: 5, fields: ["signature", "name", "file"] });
```
(also live: `getGroupRewardsAndDiscount` → get-group-rewards-and-discount.ts :4-18.)

## Verdict
Adopt copy-then-stable-sort with MAX_SAFE_INTEGER demotion and the null-filtering group triple. Adapt order vocabulary. Omit nothing.
