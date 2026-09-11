<!-- capsule-v2 -->
# cookie-silent-failure-contract — which cookie operations fail silently, and what is the unit mismatch trap?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How do you set a cookie and actually KNOW it landed?

## Read/write/delete + silent-failure matrix
**Path/Symbol:** `skills/cdp/interaction-skills/cookies.md` whole doc — read (:5–22), write (:24–46), delete/clear (:48–53), Gotchas (:55–61).
**Signature:** `Network.getCookies({urls?})` (page-scoped) vs `Storage.getCookies({})` (whole browser); `Network.setCookie({name,value,domain,path,secure,httpOnly,sameSite,expires})`; `Network.deleteCookies({name,domain})`; `Network.clearBrowserCookies()`.
**Data Shape:** scope split: Network.* = cookies visible to the attached page/context; Storage.* = EVERY cookie in the browser. `expires` is SECONDS (float since epoch), not ms. sameSite ∈ 'Strict'|'Lax'|'None'; 'None' additionally requires secure:true.

### Decisive source
```md
- `Network.setCookie` silently fails with no error if `domain` doesn't match
  any origin in the current profile — you'll get `{ success: true }` and the
  cookie just won't be there. Verify with `getCookies` after.
- `expires` is seconds (float), **not** milliseconds. A common mistake.
```

**Flow:** write → re-read getCookies to verify presence → session cookies = omit expires (or 0) → full logout = clearBrowserCookies PLUS `Storage.clearDataForOrigin({origin, storageTypes:'all'})` because clearing cookies does NOT touch localStorage/IndexedDB.
**Invariant:** Success response ≠ effect for Network.setCookie — the domain-mismatch failure is silent by contract, so post-write verification is mandatory, not paranoia. The ms-vs-s bug produces cookies that "work" until interpreted as an already-expired instant.
**Probe:** `grep -cF 'silently fails with no error' skills/cdp/interaction-skills/cookies.md` → 1; `grep -cF '**not** milliseconds' <same>` → 1; `grep -cF '`expires: 0`' <same>` → 1; `grep -cF 'clearDataForOrigin' <same>` → 1.
**Retrieve:** search_graph --project browser-harness-js --query "setCookie getCookies" resolves generated.ts wrappers line-exact.

## Verdict
Adopt verify-after-set + seconds-expires as hard rules; adapt scope choice (page vs browser) per flow. Omit sourceScheme/priority details unless cloning profiles.
