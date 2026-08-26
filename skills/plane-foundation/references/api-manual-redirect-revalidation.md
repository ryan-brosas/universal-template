<!-- capsule-v2 -->
# Manual redirect re-validation ladder — how do you follow redirects without letting a 3xx bounce you into the internal network?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** `requests` re-resolves every redirect hop and will happily follow a `Location` pointing at link-local metadata — what is the safe follow policy?

## pinned_fetch vs pinned_fetch_following_redirects
**Path/Symbol:** `apps/api/plane/utils/url_security.py`:`pinned_fetch` (:198–222), `pinned_fetch_following_redirects` (:225–272).
**Signature:** `pinned_fetch(method, url, *, allowed_ips=None, allowed_hosts=None, headers=None, timeout=30, **kwargs) -> Response`; `pinned_fetch_following_redirects(...) -> (Response, final_url)`.
**Data Shape:** two distinct policies exported deliberately: never-follow (webhook delivery) and manual-follow-with-revalidation (crawler/unfurler). Raises `ValueError` on any blocked hop, `requests.TooManyRedirects` past cap, `RequestException` on transport failure.

### Decisive source
```python
current_url = url
redirects = 0
while True:
    response, _ = _fetch_validated_hop(method, current_url, ...)   # resolve+validate+pin THIS url

    if response.status_code not in _REDIRECT_STATUSES:             # {301,302,303,307,308}
        return response, current_url
    location = response.headers.get("Location")
    if not location:
        return response, current_url
    if redirects >= max_redirects:
        response.close()
        raise requests.TooManyRedirects(f"Exceeded {max_redirects} redirects for URL: {url}")
    redirects += 1
    response.close()          # release the intermediate hop's connection/session
    current_url = urljoin(current_url, location)   # next loop iteration re-validates it
```

**Flow:** each hop is an independent validate→pin→request cycle; a redirect Location is joined against the current URL and fed back through the SAME validation; intermediate responses are closed before following; hop budget default 5.
**Invariant:** no hop is ever fetched without fresh resolution+validation of its URL — a public first hop cannot launder a private target via 302. Consumers that must not reveal redirect behavior at all use `pinned_fetch` and surface the 3xx verbatim.
**Probe:** `test_url_security.py::TestPinnedFetchRedirects::test_blocks_redirect_to_private_ip` (:271–282, second-hop ValueError propagates) + `::test_follows_and_revalidates_each_hop` (:253–267, asserts `mock_resolve.call_count == 2` with per-hop hostnames) + advisory regression `test_ssrf_advisories.py::TestWebhookRedirect::test_webhook_does_not_follow_redirects` (:170–185, asserts exactly ONE request and the 302 returned as-is). Not executed this lane (no provisioned Django deps).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "follow redirects manually revalidate each hop TooManyRedirects", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `TestPinnedFetchRedirects::test_follows_and_revalidates_each_hop` #1 and `pinned_fetch_following_redirects` :225–272 in top rows.

## Verdict
Adopt the two-policy split (never-follow for event delivery, manual re-validated follow for crawling) and per-hop resource cleanup; adapt hop budget/timeout to your product; omit Plane's specific consumers (favicon crawl, webhook POST).
