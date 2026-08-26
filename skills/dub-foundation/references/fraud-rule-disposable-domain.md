<!-- capsule-v2 -->
# Disposable-domain suspicious-email rule — Redis set membership with a fail-open Redis-outage posture

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When the disposable-domain store is unreachable, does a customer's temp-mail signup flag fraud or pass silently?

## Single sismember probe whose catch returns NOT-triggered
**Path/Symbol:** `apps/web/lib/api/fraud/rules/check-customer-email-suspicious.ts:checkCustomerEmailSuspicious` (:106-144).
**Signature:** `evaluate: async ({ customer }) => { triggered: redis.sismember("disposableEmailDomains", domain) === 1 }`.
**Data Shape:** Redis SET `disposableEmailDomains` (externally curated — no seed/maintenance code in this repo); domain extracted via `extractEmailDomain`, missing email/domain ⇒ not triggered without touching Redis.

### Decisive source
```ts
try {
  const isDisposable = await redis.sismember("disposableEmailDomains", domain);
  return { triggered: isDisposable === 1 };
} catch (error) {
  // If Redis check fails, log error but don't trigger fraud
  console.error("Error checking disposable email domain:", ...);
  return { triggered: false };
}
```
(check-customer-email-suspicious.ts :123-142)

**Flow:** email present? → domain extractable? → `SISMEMBER` → strict `=== 1` (Redis integer, not truthy coercion). Any Redis failure (timeout/conn refused) lands in catch ⇒ not triggered + error log.
**Invariant:** FAIL-OPEN on infra outage: availability of the commission pipeline beats fraud recall here — deliberate contrast with click-ingest dedup which fails CLOSED (see `click-ingest-failclosed`). The rule carries NO config (not in CONFIGURABLE merge beyond the default-enabled row) and NO local blocklist fallback; the set's freshness is an ops concern.
**Probe:** anchored at dub repo root: `grep -c 'disposableEmailDomains' apps/web/lib/api/fraud/rules/check-customer-email-suspicious.ts` = **1**; `grep -c "don't trigger fraud" apps/web/lib/api/fraud/rules/check-customer-email-suspicious.ts` = **1** (probe pattern `don.t trigger fraud`). Direct tests: E2E flow `tests/fraud/index.test.ts` (:138-176) tracks a lead with `email-temp.com` expecting the event — requires the seeded Redis set in the integration environment (recorded caveat for offline ports).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "checkCustomerEmailSuspicious", limit: 5 });
```

## Verdict
Adopt the set-membership shape and its fail-open outage posture; pair it with your own blocklist curation. Adapt storage (any set-like store) and the strict `===1` to your client's return type. Omit nothing else — the rule is deliberately minimal.
