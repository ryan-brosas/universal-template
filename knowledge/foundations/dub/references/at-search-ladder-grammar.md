<!-- capsule-v2 -->
# @-search ladder grammar — how do you implement dual-mode search where "@" means exact email, across a whole platform?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Nine list/count endpoints let users type either an email or a fuzzy name. What is the shared grammar that turns one `search` string into either an exact-match or a full-text query — and what must be sanitized before it reaches MySQL full-text search?

## Connected graph-selected seam
**Path/Symbol:** ternary-form sites (8): `apps/web/lib/customers/api/get-customers.ts:70` · `apps/web/lib/customers/api/customer-count-where.ts:36` · `apps/web/app/(ee)/api/partner-profile/programs/[programId]/customers/route.ts:65` · `.../customers/count/route.ts:57` · `.../submitted-leads/route.ts:36` · `.../submitted-leads/count/route.ts:31` · workspace twins `apps/web/app/(ee)/api/programs/[programId]/submitted-leads/route.ts:40` · `.../submitted-leads/count/route.ts:35` · if-form variant: `apps/web/lib/api/partners/program-enrollment-query.ts:buildPartnerEmailSearchWhere` (:9-36) · sanitizer `apps/web/lib/prisma/index.ts:sanitizeFullTextSearch` (:22-25).
**Signature:** every site takes an optional `search: string` and emits a Prisma where fragment; the variant additionally takes `email?` and returns `{}` when nothing is set.
**Data Shape:** output is either `{ email: <exact> }` or `{ email: { search: q }, name: { search: q } }` (variant adds `companyName` and a third exact-id arm).

### Decisive source
```ts
// THE GRAMMAR (ternary form, all 8 sites byte-isomorphic; get-customers.ts :69-76 shown)
search
  ? search.includes("@")
    ? { email: search }                                   // "@" ⇒ EXACT case-sensitive email equality
    : { email: { search: sanitizeFullTextSearch(search) },
        name:  { search: sanitizeFullTextSearch(search) } }  // else MySQL full-text over name fields
  : {}
```
```ts
// the sanitizer (lib/prisma/index.ts :22-25): strip MySQL FTS operator characters, then trim
export const sanitizeFullTextSearch = (search: string) => {
  // remove unsupported characters for full text search
  return search.replace(/[*+\-()~@%<>!=?:]/g, "").trim();
};
```
```ts
// the VARIANT (program-enrollment-query.ts :16-34): if-form + two extra arms
if (email) return { email };
if (search) {
  if (search.includes("@")) return { email: search };
  if (search.startsWith("pn_")) return { id: search };     // partner-id prefix ⇒ exact row id
  const q = sanitizeFullTextSearch(search);
  return { OR: [ { email: { search: q } }, { name: { search: q } }, { companyName: { search: q } } ] };  // THREE fields
}
return {};
```
**Flow:** parse optional search → contains "@" ⇒ exact email equality (no sanitization — the @ itself would be stripped by the sanitizer, which is why the exact arm bypasses it) → otherwise strip FTS operator chars + trim → MySQL `{ search: q }` full-text match across the resource's name fields (email+name; partners add companyName). The variant inserts an explicit-id arm (`pn_` prefix) between the two.
**Invariant:** (1) The "@" test runs on the RAW input and the exact arm bypasses sanitization — porting the sanitizer onto the exact arm would silently break every email search (the regex strips "@"). (2) Full-text arms always pass through sanitizeFullTextSearch; unsanitized user input reaching MySQL FTS changes query semantics (operators like + - * ~ are interpreted by the engine). (3) The grammar is duplicated at 9 sites as separate copies (8 ternary + 1 if-form), not a shared helper — the variant's extra arms (pn_ id, companyName) show how members diverge; a consolidation must preserve per-resource field sets. Non-search `includes("@")` uses elsewhere (companyName validity checks, trusted-partner id/email disambiguation) are a different idiom and are NOT part of this grammar.
**Probe:** No direct unit test for the ladder (it lives inline in routes). Deterministic probes executed at pin: `includes("@")` census over lib/+app/ = exactly 9 search sites (the 8 ternary + program-enrollment-query.ts:20) plus 3 non-search uses (generate-partner-network-invite-email.ts:83, get-program-network-invite-email-defaults.ts:6, admin/partners/trusted/route.ts:60) — no 10th search site; `sanitizeFullTextSearch` definition at lib/prisma/index.ts:22-25 with the operator-char regex; NEGATIVE probe: no site applies the sanitizer to the exact-email arm.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "sanitizeFullTextSearch includes @ email search", limit: 10 }); // grammar sites
await mcp.codebase_memory.search_graph({ project: "dub", query: "buildPartnerEmailSearchWhere pn_ companyName", limit: 5 }); // the variant
```

## Verdict
Adopt the dual-mode contract ("@" ⇒ exact email, else sanitized full-text over name fields) and the raw-input test ordering (test before sanitizing; never sanitize the exact arm). Extract ONE helper taking a field list instead of duplicating the ternary at every endpoint — dub's 9-site duplication is the anti-pattern to avoid, and its variant shows the extension points (explicit-id prefix arm, extra fields). Adapt the operator-character set to your database's full-text syntax. Omit the pn_-style id arm unless clients address rows by external ids in the same box. Caveat: no direct test exists; anchors are line-pinned at the pin.
