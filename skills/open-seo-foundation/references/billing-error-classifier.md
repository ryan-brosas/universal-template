<!-- capsule-v2 -->
# Billing error classifier — how do you map vendor balance failures to one typed error without misclassifying unrelated endpoint errors?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** Which status codes and text signals constitute a billing failure, and how is classification scoped per API section?

## Path-prefix-scoped balance-failure classifier
**Path/Symbol:** `src/server/lib/dataforseoBillingClassification.ts:createDataforseoBillingClassifier` (:28-48).
**Signature:** `function createDataforseoBillingClassifier(config: { pathPrefix: string; billingIssueCode: ErrorCode; billingIssueMessage: string }): (status: number | undefined, details: string, path: string) => AppError | null`.
**Data Shape:** `BILLING_STATUS_CODES = {40200, 40210, 402}`; `BILLING_SIGNALS` substrings: "insufficient funds", "balance is too low", "payment required", "billing", "balance", "problem billing", "recharged".

### Decisive source
```ts
return (status, details, path) => {
  if (!path.includes(config.pathPrefix)) return null;   // scope to this section only
  const text = details.toLowerCase();
  const matchesBillingStatus = status != null && BILLING_STATUS_CODES.has(status);
  const matchesBillingText = BILLING_SIGNALS.some((signal) => text.includes(signal));
  if (matchesBillingStatus || matchesBillingText) {
    return new AppError(config.billingIssueCode, config.billingIssueMessage);
  }
  return null;
};
```

**Flow:** the classifier returned by this factory is handed to `assertOk`'s `classify` option per section (`pathPrefix` e.g. `/v3/backlinks`) → on any failed response/task it returns the section's typed billing AppError when the vendor status OR message text signals a depleted balance → returning null lets assertOk fall through to the charged-task / INTERNAL_ERROR ladder. Feature-enablement is deliberately NOT classified anymore (backlinks/AI-search are in every account) — balance is the only account-level failure.
**Invariant:** A classifier must return null for out-of-scope paths so one section's matcher can't swallow another's errors; text matching lowercases first and matches substrings because vendors phrase balance failures inconsistently across endpoints.
**Probe:** `src/server/lib/dataforseoBillingClassification.test.ts` (status/text/path-prefix matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "createDataforseoBillingClassifier BILLING_STATUS_CODES pathPrefix classify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt factory-per-section classifiers that return null outside their prefix, with code-OR-text matching for money errors. Adapt signal strings/codes to your vendor's actual vocabulary. Omit multi-account feature gating if your vendor has none.
