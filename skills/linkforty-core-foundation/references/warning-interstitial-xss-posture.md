<!-- capsule-v2 -->
# Warning interstitial XSS posture — safeHref protocol allowlist beats escapeHtml because schemes contain nothing it neutralises

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** Why is HTML-escaping insufficient when rendering an untrusted flagged destination into an href?

## safeHref http(s) gate + no-JS warning page
**Path/Symbol:** `src/lib/link-safety.ts:safeHref` (:64-72), `escapeHtml` (:75-82), `generateWarningLinkHTML` (:94-157).
**Signature:** `function safeHref(destination: string): string | null` — null unless `url.protocol === 'http:' || 'https:'`.
**Data Shape:** Null return means caller renders inert text instead of an anchor (an `href=""` would re-request the warning page); bare deep-link paths parse as relative URLs against the redirect host and are therefore rejected too.

### Decisive source
```ts
// link-safety.ts:47-57 (doc comment) + :64-72
// `escapeHtml` is not sufficient on its own: a URL scheme contains none of the
// characters it neutralises, so `javascript:alert(1)` passes through untouched and
// becomes executable on click. That matters here more than almost anywhere else —
// this page is shown *only* for links already flagged as suspicious ...
// zod's `.url()` accepts `javascript:` and `data:` URLs, so a stored destination
// can already hold one.
return url.protocol === 'http:' || url.protocol === 'https:' ? destination : null;
```

**Flow:** warn outcome → destination shown in full (the point is to un-hide what the short link hid), escaped via escapeHtml for text contexts → continue-anchor rendered ONLY if safeHref passes → `rel="nofollow noopener noreferrer"` on the anchor → optional abuse-report link → zero JavaScript and zero external assets so it renders on a bare redirect host under strict CSP; response carries `X-Robots-Tag: noindex, nofollow` + `Cache-Control: no-store` (redirect.ts :288-289).
**Invariant:** Write-time validation tightening may happen separately but this read-side page must NOT depend on it having happened (defense at the hostile-input boundary); every interpolation into markup goes through escapeHtml including reportUrl.
**Probe:** `bash -c "grep -cF 'becomes executable on click' src/lib/link-safety.ts"` → 1 (:51) and `bash -c "grep -cF '.url()' src/lib/link-safety.ts"` → 1 (:55, inside backticks — never shell-interpolate this pattern unquoted); direct tests `src/lib/link-safety.test.ts` describe('escapeHtml') + describe('generateWarningLinkHTML'); route-level pins in `src/routes/redirect.safety.test.ts` describe('a link flagged to warn') incl. "records NO click" and noindex/no-cache header cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "safeHref javascript protocol warning html", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt protocol-allowlisting (not escaping) as the href gate on any page rendering attacker-influenced destinations, especially post-flag pages where input hostility is highest; adapt the allowlist if you serve non-http schemes deliberately; omit the CSP-zero-dependency constraint only for authenticated admin surfaces.
