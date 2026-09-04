<!-- capsule-v2 -->
# Safe-redirect whitelist — the regex that lets relative paths through but not protocol-relative URLs

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** How do you honor a `?url=` post-login redirect without handing attackers an open redirect?

## Single-slash-relative check, then whitelist, then fallback '/'
**Path/Symbol:** `sections/security/saferedirects.md` (vulnerable example :9-20, fix :24-47).
**Signature:** `getValidRedirect(url): string` — returns domain-prefixed path, whitelisted URL, or `'/'`.
**Data Shape:** whitelist = plain object map of approved absolute origins; the guard is one anchored regex.

### Decisive source
```javascript
// saferedirects.md :26-38 — the whole contract
const whitelist = { 'https://google.com': 1 };
function getValidRedirect(url) {
  if (url.match(/^\/(?!\/)/)) {          // starts with ONE slash (not //)
    return 'https://example.com' + url;  // pin to own origin
  }
  return whitelist[url] ? url : '/';     // else whitelist or fall back home
}
```

**Flow:** attacker posts crafted links on public forums (:6); unguarded `res.redirect(req.query.url)` bounces users to lookalike domains ("examp1e.com", :56). The regex `^\/(?!\/)` is load-bearing: `/dashboard` → same-origin path; **`//evil.com` → protocol-relative URL that would escape your origin — negative lookahead rejects it** into the whitelist branch. Whitelisted absolute URLs pass only if they match a key exactly.
**Invariant:** never trust user input as the redirect basis at all (:53 "don't use unvalidated user input"); when you must, the two-branch structure (relative→prefix / absolute→whitelist / else→`'/'`) is complete — any fourth path reintroduces the hole.
**Probe:** no runner upstream. Deterministic probe: `grep -cF '(?!\/)' sections/security/saferedirects.md` >= 1 && `grep -c 'whitelist' sections/security/saferedirects.md` >= 3.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "validation", "limit": 10}'
# resolves `sections/security/saferedirects.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the function shape verbatim for login/return-URL flows. Adapt the whitelist backing store to config/DB. Omit allow-from-style header alternatives — this is the request-side control.
