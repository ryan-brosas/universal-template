<!-- capsule-v2 -->
# Partner payout methods surface — how does the settings API present each rail's connection state without leaking credentials?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the shape of the payout-method list a partner sees, and how are identifiers masked per rail?

## getPartnerPayoutMethods: country gate → per-rail probe → masked identifier rows
**Path/Symbol:** `apps/web/lib/payouts/get-partner-payout-methods.ts:getPartnerPayoutMethods` (:15-107); country allowlist `apps/web/lib/partners/get-payout-methods-for-country.ts`; bank account probe `apps/web/lib/partners/get-partner-bank-account.ts`.
**Signature:** `getPartnerPayoutMethods(partner: Pick<Partner,"id"|"country"|"stripeConnectId"|"stripeRecipientId"|"paypalEmail"|"defaultPayoutMethod"|"tremendousEmail">): Promise<PartnerPayoutMethodSetting[]>` where setting = `{type, label, default, connected, identifier:string|null}`.
**Data Shape:** stablecoin identifier = `addr.slice(0,6)••••addr.slice(-4)` (short addresses shown raw); connect = `routing••••last4` or `••••last4`; paypal/tremendous = raw email; tremendous appears ONLY when tremendousEmail set (:88 comment: "only when connected via the referral embed").

### Decisive source
```ts
if (availablePayoutMethods.includes(PartnerPayoutMethod.stablecoin)) {
  let identifier: string | null = null;
  if (stripePayoutMethod?.crypto_wallet)
    identifier = address.length > 10 ? `${address.slice(0, 6)}••••${address.slice(-4)}` : address;
  payoutMethods.push({ type, label: "Stablecoin",
    default: partner.defaultPayoutMethod === type,
    connected: Boolean(stripePayoutMethod?.crypto_wallet), identifier });
}
```
(:36-52 pattern repeated for connect/paypal/tremendous)

**Flow:** country decides which rails are even offered → parallel Stripe probes (bank account via Connect, crypto wallet via v2 recipient) → each offered rail becomes a row with connected=probe-result (or mere-email-presence for paypal/tremendous), default flag from the partner row. UI drives enable/disable flows off `connected`, and the default radio writes back through recomputePartnerPayoutState.
**Invariant:** (1) `connected` reflects LIVE provider state, not stored fields — a partner with a stale paypalEmail still sees PayPal "connected" until recompute clears it, so this view intentionally lags the truth-checking plane; (2) identifiers are display-safe by construction — full wallet addresses or account numbers never enter the payload; (3) unoffered rails are ABSENT, not present-with-connected:false.
**Probe:** deterministic probe: `grep -c 'availablePayoutMethods.includes' apps/web/lib/payouts/get-partner-payout-methods.ts` = 3; `grep -n 'routing_number' apps/web/lib/payouts/get-partner-payout-methods.ts` = :62. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getPartnerPayoutMethods", limit: 5 });
```

## Verdict
Adopt the probe-driven settings projection with per-rail masking rules. Adapt labels/countries. Omit the referral-embed gating for Tremendous if you have no gift-card onboarding path.
