<!-- capsule-v2 -->
# Customer-email-match three-tier rule — exact, domain, and historical-domain tiers, and why the domain tier refuses free-mail providers

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** In what order do the three match tiers fire, and which guard keeps `gmail.com` customers from matching every other gmail partner?

## Ordered ladder with a generic-email firewall before tier 2
**Path/Symbol:** `apps/web/lib/api/fraud/rules/check-customer-email-match.ts:checkCustomerEmailMatch` (:11-100).
**Signature:** `evaluate: async ({ program, partner, customer }: FraudEventContext) => Promise<FraudTriggeredRule>` — metadata carries `{ matchType: CustomerEmailMatchType.EXACT | DOMAIN_MATCH | HISTORICAL_DOMAIN_MATCH }`.
**Data Shape:** missing either email ⇒ not triggered; domains extracted via `extractEmailDomain`; historical probe = Prisma `customer.findFirst` in the same program+partner excluding current customer.

### Decisive source
```ts
if (normalizedPartnerEmail === normalizedCustomerEmail) return { triggered: true, metadata: { matchType: EXACT } };
...
// Skip domain matching for free email providers
if (isGenericEmail(customer.email)) return { triggered: false };
if (partnerEmailDomain === customerEmailDomain) return { triggered: true, metadata: { matchType: DOMAIN_MATCH } };
// 3. Historical: only when (field present AND true) OR field absent
const shouldCheckHistoricalDomainMatch =
  ("isFirstConversion" in customer && customer.isFirstConversion) ||
  !("isFirstConversion" in customer);
const previousCustomer = await prisma.customer.findFirst({
  where: { programId: program.id, partnerId: partner.id, id: { not: customer.id },
           email: { endsWith: `@${customerEmailDomain}` } },
  select: { id: true } });
```
(check-customer-email-match.ts :26-84 condensed)

**Flow:** normalize BOTH emails (plus-tag strip all domains; dot-strip gmail/googlemail) → tier 1 exact → generic-provider firewall (`isGenericEmail(customer.email)`) → tier 2 same-domain → tier 3 historical: any PRIOR customer of this partner in this program whose email ends with `@<customer's domain>`.
**Invariant:** (1) the generic-email check tests the CUSTOMER's address and runs BEFORE domain matching — without it every gmail/gmail or yahoo/yahoo pair would false-positive; EXACT matches still fire for free providers (normalization makes `first.last+shop@gmail.com` ≡ `firstlast@gmail.com`); (2) tier 3 fires on first-conversion OR legacy contexts lacking `isFirstConversion` (the `"in"` check) — repeat conversions skip the extra query; (3) historical search is scoped to program+partner and excludes the triggering customer itself; (4) `endsWith` is suffix-match, so `@mail.google.com` would NOT match `google.com` but subdomain-of-domain emails do share suffixes — porters wanting FQDN equality must add it.
**Probe:** anchored at dub repo root: `grep -o 'isGenericEmail' apps/web/lib/api/fraud/rules/check-customer-email-match.ts | wc -l` = **2** (import + call); `grep -c 'endsWith' apps/web/lib/api/fraud/rules/check-customer-email-match.ts` = **1**; `grep -o 'isFirstConversion' apps/web/lib/api/fraud/rules/check-customer-email-match.ts | wc -l` = **3**. Direct tests: `tests/fraud/index.test.ts` covers ALL THREE tiers over HTTP — exact (:18-62), domain (:64-100), historical via `emailDomain:"google.com"` (:102-136) asserting metadata matchType per tier.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "checkCustomerEmailMatch", limit: 5 });
```

## Verdict
Adopt the three-tier order and the free-mail firewall placement (between exact and domain). Adapt the generic-provider list and normalization rules. Omit nothing — order is the contract.
