<!-- capsule-v2 -->
# Reward amount & cents normalization — the two 10-line kernels every reward path assumes

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How is a reward's payable amount derived, and how do bigint Prisma cents become JS numbers at the boundary?

## getRewardAmount + serializeReward + toCentsNumber
**Path/Symbol:** `apps/web/lib/partners/get-reward-amount.ts:getRewardAmount` (:3-11); `apps/web/lib/api/partners/serialize-reward.ts:serializeReward` (:6-14); `packages/utils/src/functions/to-cents-number.ts:toCentsNumber` (:5-10).
**Signature:** `getRewardAmount({type, amountInCents, amountInPercentage}): number`; `serializeReward(reward: Reward)`; `toCentsNumber(value: number|bigint|null|undefined): number`.
**Data Shape:** type "flat" reads amountInCents; percentage reads amountInPercentage (Decimal column); anything null/undefined ⇒ 0.

### Decisive source
```ts
export const getRewardAmount = ({
  type,
  amountInCents,
  amountInPercentage,
}: Pick<RewardProps, "type" | "amountInCents" | "amountInPercentage">) => {
  const amount = type === "flat" ? amountInCents : amountInPercentage;

  return amount === null || amount === undefined ? 0 : amount;
};
```
(get-reward-amount.ts :3-11)

and

```ts
export function serializeReward(reward: Reward) {
  return {
    ...reward,
    amountInPercentage:
      reward.amountInPercentage != null
        ? Number(reward.amountInPercentage)
        : null,
  };
}
```
(serialize-reward.ts :6-14 — file opens with `import "server-only"`)

**Flow:** every consumer (determinePartnerReward's zero-check, evaluateRewardConditions' winner sort) funnels through getRewardAmount AFTER serializeReward has flattened Prisma.Decimal → number; toCentsNumber handles the pre/post-migration duality (`typeof value === "bigint" ? Number(value) : value`, null ⇒ 0) for commissions and link saleAmount.
**Invariant:** a percentage reward with amountInPercentage=null scores 0 in the winner-sort and is dropped by determinePartnerReward's `amount === 0` gate — "zero-value" is the universal no-payout sentinel, not an error. serializeReward exists because Prisma.Decimal must never cross to the client or into arithmetic; forgetting it yields object-typed amounts that silently break comparators.
**Probe:** deterministic probes (repo root): `grep -n 'type === "flat"' apps/web/lib/partners/get-reward-amount.ts` → :8; `grep -n 'server-only' apps/web/lib/api/partners/serialize-reward.ts` → :2; `grep -n 'Number(reward.amountInPercentage)' apps/web/lib/api/partners/serialize-reward.ts` → :11; `cat packages/utils/src/functions/to-cents-number.ts` contains both `value == null` and the bigint ternary. Direct tests: click/lead/sale-reward.test.ts suites pin end-to-end amounts (runner offline-blocked, standing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "getRewardAmount", limit: 5, fields: ["signature", "name", "file"] });
```
(also live: `serializeReward` → api/partners/serialize-reward.ts :6-14 rank#1; `toCentsNumber` → packages/utils .../to-cents-number.ts :5-10.)

## Verdict
Adopt all three kernels verbatim — they are dependency-free. Adapt money type. Omit nothing.
