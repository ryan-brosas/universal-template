<!-- capsule-v2 -->
# Branded-tag arbitration — how do users override a computed classification without breaking analytics?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What is the precedence rule when system-computed branded status meets user tags?

## One-sided override; both-tags = system wins
**Path/Symbol:** `packages/lib/src/tag-utils.ts:getEffectiveBrandedStatus` (L26–55), `isPromptBranded` (L57–72), `computeSystemTags` (L74–77), `sanitizeUserTags` (L87–92).
**Signature:** `getEffectiveBrandedStatus(systemTags: string[], userTags: string[]): { isBranded, isOverridden, systemIsBranded }`.
**Data Shape:** all comparisons case-insensitive; "branded"/"unbranded" ARE legal user tags — they exist specifically as the override channel. System classification: prompt contains brand name OR domain OR domain-without-TLD (`domain.split(".")[0]`) as lowercase substring.

### Decisive source
```ts
if (hasBrandedUserTag && !hasUnbrandedUserTag) return { isBranded: true,  isOverridden: !systemIsBranded, systemIsBranded };
if (hasUnbrandedUserTag && !hasBrandedUserTag) return { isBranded: false, isOverridden: systemIsBranded,  systemIsBranded };
return { isBranded: systemIsBranded, isOverridden: false, systemIsBranded };  // both or neither → system
```

**Flow:** computeSystemTags stamps exactly one system tag at creation/report time; user tags sanitize (trim/dedupe/keep empties out); effective status resolves per display/filter. The `domainWithoutTld` term makes "acme pricing" count as branded for acme.com even though bare TLD-less strings are noisy — accepted trade.
**Invariant:** an ambiguous override (both tags) must never silently pick a side — it defers to the system and reports `isOverridden: false`. `isOverridden` exists so audits can distinguish model-classified from human-forced rows.
**Probe:** `packages/lib/src/tag-utils.test.ts` (GREEN in probe run; both/neither/one-sided matrices).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "getEffectiveBrandedStatus isPromptBranded computeSystemTags SYSTEM_TAGS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-sided-override truth table verbatim for any computed+user-editable classification; adapt tag vocabulary; omit domainWithoutTld only with eyes open (it changes what counts as branded).
