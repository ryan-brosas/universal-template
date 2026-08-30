<!-- capsule-v2 -->
# LinkedIn URL canonicalization — how do I normalize ANY profile-ish link (bare path, full URL, Sales Nav, trailing junk) into one canonical form?

**Source:** linvo-scraper ISC `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** What is the minimal total function that turns arbitrary user/CRM-supplied LinkedIn links into a canonical `/in/<slug>` (optionally re-prefixed), and which inputs must it refuse?

## The normalizer
**Path/Symbol:** `lib/helpers/create.linkedin.url.ts:createLinkedinLink` (:1–17); consumers: `linkedin.message.with.view.ts` (visit target) and `connect-outreach-ladder` (post-redirect id extraction).
**Signature:** `createLinkedinLink(getLink: string, fullLinkedinUrl: boolean): string`.
**Data Shape:** accepts bare paths (`/in/slug`, `/sales/people/<composite>`), absolute URLs with any host spelling, trailing slashes/backslashes; returns `''` for non-profile input — the empty string IS the failure value.

### Decisive source
```ts
if (!getLink || (getLink.indexOf('/in/') === -1 && getLink.indexOf('/sales/people/') === -1)) {
  return '';                                   // gate: only profile-shaped links proceed
}
const link = getLink?.trim()?.replace(/\\/g, '');
const newLink = 'https://www.linkedin.com' +
  (link.indexOf('linkedin.com') > -1 ? link.split('linkedin.com')[1] : link);
const prepend = fullLinkedinUrl ? 'https://www.linkedin.com' : '';
const path = new URL(newLink).pathname;        // query + fragment dropped HERE
if (path[path.length - 1] === '/') return prepend + path.slice(0, -1);
return prepend + path;
```

**Flow:** shape-gate FIRST (`/in/` or `/sales/people/` must appear, else `''`) → trim + strip backslashes → if a host is present, split on `linkedin.com` and keep the tail; else treat as path → run through `new URL().pathname` so query strings and fragments vanish → drop exactly ONE trailing slash. The boolean picks prefixed-absolute vs path-only output.
**Invariant:** canonicalization is TOTAL — every input yields either a usable link or `''`, never a throw. The gate-before-parse ordering means malformed URLs can never reach the `new URL()` constructor and blow up. This is the client-side twin of sales-nav-lead-identity's server-side composite-URN→canonical-slug ladder; both end at "one person = one path".
**Probe:** no dedicated test file in-repo (coverage caveat: source-read at pinned HEAD cfbe910); behavior indirectly pinned by outreach/message service specs that feed canonical URLs downstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "createLinkedinLink", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim as the entry-point normalizer for any LinkedIn automation accepting external link lists. Adapt the shape-gate to your entity types (`/company/`, posts). Omit nothing — 17 lines, total function.
