<!-- capsule-v2 -->
# Partner payout-state recompute — how do you derive a partner's default payout method and payoutsEnabledAt from live provider state without clobbering their choice?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When multiple payout methods connect/disconnect out-of-band, what are the rules for re-deriving the partner's payout state — and what does the caller do with the diff?

## recomputePartnerPayoutState: capability-checked priority ladder + sticky default
**Path/Symbol:** `apps/web/lib/payouts/recompute-partner-payout-state.ts:recomputePartnerPayoutState` (:7-140); UI mirror `apps/web/lib/payouts/get-partner-payout-methods.ts:getPartnerPayoutMethods` (:15-107); Stripe v2 crypto-wallet probe `apps/web/lib/stripe/get-stripe-recipient-payout-method.ts:4-26`.
**Signature:** `recomputePartnerPayoutState(partner: Pick<Partner,"stripeConnectId"|"stripeRecipientId"|"paypalEmail"|"payoutsEnabledAt"|"defaultPayoutMethod"|"tremendousEmail">): Promise<{payoutsEnabledAt, defaultPayoutMethod, activePayoutMethods, cryptoWalletAddress, cryptoWalletNetwork, maskedCryptoWalletAddress, hasPayoutStateChanged}>`.
**Data Shape:** PAYOUT_METHOD_PRIORITY = `[stablecoin, connect, paypal, tremendous]` (:7-12); active = capability-gated booleans; masked wallet = `addr.slice(0,6)••••addr.slice(-4)` when length>10.

### Decisive source
```ts
const connectActive  = Boolean(connectAccount?.payouts_enabled === true &&
    connectAccount?.capabilities?.transfers === "active");
const stablecoinActive = Boolean(hasCryptoWalletCapabilities && cryptoWalletAddress && cryptoWalletNetwork);
const paypalActive     = Boolean(partner.paypalEmail);      // mere email presence
const tremendousActive = Boolean(partner.tremendousEmail);  // referral-embed only
const hasValidDefaultPayoutMethod = partner.defaultPayoutMethod &&
    activePayoutMethods.includes(partner.defaultPayoutMethod);
const defaultPayoutMethod = hasValidDefaultPayoutMethod ? partner.defaultPayoutMethod : activePayoutMethods[0] ?? null;
```
(:55-93)
```ts
if (defaultPayoutMethod !== partner.defaultPayoutMethod) payoutsEnabledAt = new Date();
else if (partner.payoutsEnabledAt) payoutsEnabledAt = partner.payoutsEnabledAt;
else payoutsEnabledAt = new Date();
```
(:94-107)

**Flow:** parallel-retrieve Connect account + recipient account → stablecoin active requires recipient capabilities.crypto_wallets.status==="active" AND a resolvable wallet (address+network) via the Stripe v2 payout_methods probe filtered to `type==="crypto_wallet"` → filter the fixed priority list by actives → sticky-default rule above (changed default RESETS payoutsEnabledAt to now, so program-side eligibility flips atomically with the method switch) → return `hasPayoutStateChanged` so callers can trigger notifications; the settings-plane twin (`get-partner-payout-methods`) walks the same four methods building `{type,label,default,connected,identifier}` rows for UI, with bank identifiers as `routing••••last4` and Tremendous shown only when connected.
**Invariant:** (1) presence of credentials ≠ active rail — Connect demands BOTH payouts_enabled AND transfers capability, stablecoin demands an ACTIVE crypto-wallet capability plus a concrete wallet, while paypal/tremendous are email-presence rails; porters who trust stored emails alone will pay dead accounts; (2) the existing default WINS while still active — never silently reassign a partner's choice; (3) payoutsEnabledAt resets exactly when the default CHANGES, not on any other transition.
**Probe:** deterministic probe: `grep -n 'PAYOUT_METHOD_PRIORITY' apps/web/lib/payouts/recompute-partner-payout-state.ts | head -1` = :7; `grep -c 'activePayoutMethods.includes' apps/web/lib/payouts/recompute-partner-payout-state.ts` = 1. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "recomputePartnerPayoutState", limit: 5 });
```

## Verdict
Adopt the capability-gated activity matrix and sticky-default-with-reset contract for any multi-rail payout onboarding. Adapt the method enum and provider probes. Omit country gating details (`getPayoutMethodsForCountry`) unless your rails vary by jurisdiction.
