<!-- capsule-v2 -->
# PayPal OAuth callback — verified-email connect, capability recompute, and P2002-as-taken error surfacing

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does a partner connect their PayPal account, and which failure classes surface as friendly redirect params?

## GET /api/paypal/callback
**Path/Symbol:** `apps/web/app/(ee)/api/paypal/callback/route.ts:GET` (:13-116); env switch `apps/web/lib/paypal/env.ts:paypalEnv` (:1-13).
**Signature:** `GET(req: Request): Promise<Response>` — Next.js redirect-based (never JSON).
**Data Shape:** OAuth state carries `contextId` = the USER id being connected; success writes `{paypalEmail, payoutsEnabledAt, defaultPayoutMethod}` onto Partner; errors redirect `/payouts?settings=true&error=<code>`.

### Decisive source
```ts
if (!paypalUser.email_verified) {
  throw new Error("paypal_email_not_verified");
}

const { partner } = await prisma.partnerUser.findUniqueOrThrow({
  where: {
    userId_partnerId: {
      userId: session.user.id,
      partnerId: defaultPartnerId,
    },
  },
  include: {
    partner: true,
  },
});

const { payoutsEnabledAt, defaultPayoutMethod } =
  await recomputePartnerPayoutState({
    ...partner,
    paypalEmail: paypalUser.email,
  });
```
(callback/route.ts :53-73)

and

```ts
if (
  e instanceof Prisma.PrismaClientKnownRequestError &&
  e.code === "P2002"
) {
  error = "paypal_account_already_in_use";
} else {
  error = e.message;
}
```
(:103-110)

**Flow:** dev-ngrok host self-redirect preserving query → session gate (no user ⇒ /login) → exchangeCodeForToken → verify contextId user EXISTS (findUniqueOrThrow) → fetch PayPal profile → email_verified REQUIRED else `paypal_email_not_verified` → resolve session's default partner via partnerUser compound id → recomputePartnerPayoutState over the partner with the NEW paypal email to derive payout capability fields → persist all three columns → waitUntil confirmation email when both emails present → ANY thrown error funnels to a single catch mapping Prisma P2002 unique-violation ⇒ `paypal_account_already_in_use`, everything else ⇒ raw message → final redirect always lands on /payouts?settings=true.
**Invariant:** recompute BEFORE write means capability flags are consistent with the email actually stored (calling recompute after update would race); the contextId-vs-session double identity check prevents a state-forged connect targeting another user; P2002 is the DB-level guard enforcing one partner per PayPal account — pre-checks would lose races.
**Probe:** deterministic probes (repo root): `grep -n 'email_verified' "apps/web/app/(ee)/api/paypal/callback/route.ts"` → :53; `grep -n 'recomputePartnerPayoutState' ...` → :2/:70; `grep -n 'P2002' ...` → :105; `grep -n 'contextId' ...` → :40/:45; env sandbox split: `grep -c 'sandbox' apps/web/lib/paypal/env.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "exchangeCodeForToken", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verified-email gating, recompute-before-write capability derivation, and P2002-mapped error redirects. Adapt OAuth provider/redirect style. Omit the email template body.
