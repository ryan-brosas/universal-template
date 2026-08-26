<!-- capsule-v2 -->
# Me-cache memoization — Where does client metadata live, which keys populate when, and what stays absent on the cookies-direct construction path?

**Source:** open-linkedin-api MIT `main@5feee360ec26`; Codebase Memory `open-linkedin-api`. **Question:** How do I memoize the authenticated user's own profile read-through on a client-scoped dict, and what does each construction path leave in that dict?

## Client-scoped metadata dict + lazy /me read-through
**Path/Symbol:** `open_linkedin_api/linkedin.py:Linkedin.get_user_profile` (:1335–1348); `open_linkedin_api/client.py:Client.__init__` (:51–63, `self.metadata = {}` at :59), `Client.authenticate` (:91–102, `_fetch_metadata()` at :98 cache-path and :102 password-path), `Linkedin.__init__` (:76–80 cookies-direct branch).
**Signature:** `get_user_profile(use_cache=True) -> Dict`; `metadata: dict` initialized empty in `Client.__init__`.
**Data Shape:** keys observed: `clientApplicationInstance` (JSON-decoded `<meta name=applicationInstance>` content) and `clientPageInstanceId`, both written only by the auth-time homepage scrape; `me`, written lazily by `get_user_profile`. Miss predicate `not self.client.metadata.get("me")` treats ABSENT and EMPTY-dict alike as a miss.

### Decisive source
```python
# linkedin.py :1341–1348
        me_profile = self.client.metadata.get("me", {})
        if not self.client.metadata.get("me") or not use_cache:
            res = self._fetch(f"/me")
            me_profile = res.json()
            # cache profile
            self.client.metadata["me"] = me_profile

        return me_profile
```

**Flow:** construct Client (`metadata = {}`) → auth path: cookie-cache OR password login both end in `_fetch_metadata()` scrape → later, any `get_user_profile()` call either hits `metadata["me"]` or fetches `/me` once and writes it back; `use_cache=False` forces a refetch and overwrites.
**Invariant:** the cache is the SHARED client metadata dict — one store serves auth metadata and profile memoization. DECISIVE PATH GAP: when `Linkedin(username, password, cookies=...)` is constructed with cookies directly, `authenticate()` is bypassed entirely (linkedin.py :76–80), so `_fetch_metadata` NEVER runs and `clientApplicationInstance`/`clientPageInstanceId` stay permanently absent; only `me` can ever appear. Ports that need instance metadata must not assume its presence from a cookies-built session.
**Probe:** no upstream tests exist — source-grounded grep at HEAD: `metadata.get("me"` resolves :1341/:1342; `metadata["me"]` write :1346; `/me"` fetch :1343; `self.metadata = {}` client.py:59; `_fetch_metadata` call sites client.py:98/:102 (def :104).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "open-linkedin-api", function_name: "get_user_profile", direction: "both" });
// callees: Linkedin._fetch + CookieRepository plane; callers_total 0 (leaf consumer API)
await mcp.codebase_memory.trace_path({ project: "open-linkedin-api", function_name: "_fetch_metadata", direction: "inbound" });
// callers: Client.authenticate (+ Linkedin.__init__ via client call) — observed this pass
```

## Verdict
Adopt lazy read-through memoization keyed on one client-scoped dict with an explicit force-refresh toggle, and the honest miss predicate that collapses absent/empty. Adapt key names to your domain; keep auth-scrape writes separate from profile memo writes even in one dict. Omit the HTML-scrape mechanics themselves (owned by voyager-password-auth-metadata). Contrast twin: private-api's own-profile-bootstrap resolves /me by DELEGATION (server-side chain), never caching — use this capsule when you want the cheap local memo instead. Coverage caveat: no upstream tests; coverage check on linkedin.py + client.py = no_recorded_issue + metadata_match.
