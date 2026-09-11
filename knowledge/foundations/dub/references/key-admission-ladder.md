<!-- capsule-v2 -->
# Key admission ladder — how do you accept arbitrary user-chosen short-link slugs without collisions, phishing, or reserved-path takeover?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What is the full normalize-then-authorize pipeline between "user typed a key" and "row written"?

## processKey (normalize) + keyChecks (authorize)
**Path/Symbol:** `apps/web/lib/api/links/utils/process-key.ts:processKey` (8-41); `apps/web/lib/api/links/utils/key-checks.ts:keyChecks` (12-89); random generation `apps/web/lib/api/links/process-link.ts:278-283` (`getRandomKey({ domain, prefix, length: keyLength })`).
**Signature:** `processKey({ domain, key }): string | null` (null = reject); `keyChecks({ domain, key, workspace? }): Promise<{ error: string | null, code?: ErrorCode }>`.

### Decisive source
```ts
// processKey — pure normalization; _root bypasses everything
export function processKey({ domain, key }) {
  if (key === "_root") return key;
  if (!validKeyRegex.test(key)) return null;
  if (key.startsWith("_")) return null;      // _ prefix reserved for app routes
  if (isUnsupportedKey(key)) return null;
  key = key.replace(/^\/+|\/+$/g, "");       // trim leading/trailing slashes
  // anti-phishing: strip diacritics ONLY on Dub-owned domains (typo-squat defense);
  // custom domains keep unicode since only the workspace can set keys there
  if (isDubDomain(domain)) {
    key = key.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }
  return punyEncode(key);                    // final IDN-ascii form
}
```
```ts
// keyChecks — ordered policy ladder, first hit wins
if ((key.length === 0 || key === "_root") && workspace?.plan === "free")
  return { error: "...root redirect is Pro...", code: "forbidden" };          // :21-27
if (isReservedKeyGlobal(key))                                                 // :29-34
  return { error: `${key} is a reserved path...`, code: "forbidden" };
const link = await checkIfKeyExists({ domain, key });                         // :36-42
if (link) return { error: "Duplicate key: This short link already exists.", code: "conflict" };
if (isDubDomain(domain)) {
  if (domain === "dub.sh" || domain === "dub.link") {
    if (DEFAULT_REDIRECTS[key] || RESERVED_SLUGS.includes(key))               // :46-51 phantom rows
      return { error: "Duplicate key: ...already exists.", code: "conflict" };
    if (await isBlacklistedKey(key))                                          // :52-57 remote edge-config
      return { error: "Invalid key.", code: "unprocessable_entity" };
  }
  if (key.length <= 3 && freePlan) return { error: "...3 characters or less on Pro...", code: "forbidden" };
  if (domain === "dub.link" && key.length <= 5 && plan <= pro) return { /* Business gate */ };
  if ((await isReservedUsername(key)) && freePlan)                            // :75-84 premium usernames
    return { error: "This is a premium key...", code: "forbidden" };
}
return { error: null };
```

**Flow:** empty key ⇒ server-minted random via `getRandomKey` (collision-checked generation, honors `prefix`/`keyLength`); otherwise processKey normalizes (regex → `_` reservation → slash trim → domain-scoped NFKD-diacritic strip → punycode) and any null aborts with 422 "Invalid key."; survivors run keyChecks' ladder: plan-gated `_root` → global reserved paths → live duplicate lookup → Dub-domain-only extras (built-in redirect/reserved slug tables treated AS duplicates, remote blacklist, length-tiered plan gates, premium usernames).
**Invariant:** Normalization is PURE and domain-parameterized — the SAME user input yields DIFFERENT stored keys on dub.sh (ascii-stripped) vs a custom domain (unicode kept), so you can never compare a raw submitted key against the DB; always compare post-processKey/post-encode forms. Reserved/redirect slug lists act as PHANTOM OCCUPANCY: they conflict-check without DB rows. Policy ladders are ordered cheapest/most-static first (local constants → one indexed point-read → remote edge-config calls last). Uniqueness itself is enforced by the DB `domain_key` compound unique — the ladder is UX, not the guarantee (race-safe writes come from the DB constraint).
**Probe:** no direct unit test for processKey/keyChecks (coverage caveat — exercised only via integration). Deterministic probe: `processKey({domain:"dub.sh",key:"café"})` → `cafe`; `processKey({domain:"acme.com",key:"café"})` → punycode of "café" (diacritics kept); `processKey({domain:"x",key:"_next"})` → null; `keyChecks({domain:"dub.sh",key:"discord",workspace:{plan:"free"}})` → forbidden reserved.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "processLink keyChecks processKey", limit: 5 });
// → utils.process-key.processKey @ 8-41 · utils.key-checks.keyChecks @ 12-89
```

## Verdict
Adopt the two-stage normalize-then-authorize split with a pure, domain-parameterized normalizer returning null-as-reject, phantom-occupancy constant tables, and static-first ladder ordering. Adapt the specific reserved lists, length tiers, and premium-key monetization. Omit the edge-config blacklist if you have no remote policy store.
