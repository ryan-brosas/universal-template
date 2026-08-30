<!-- capsule-v2 -->
# Twitch GQL scrape — how does a hardcoded public Client-ID power an unauthenticated GraphQL fetch, and why does it bypass its own proxy on failure?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What is the public-GQL contract (Client-ID header, raw query string, errors[] gate) and when is failing over to direct egress correct?

## Public client-id + %s-interpolated query + proxy→direct failover
**Path/Symbol:** `app/scrapers/twitch.py:CLIENT_ID` (:23), `scrape_profile` (:26-112), `_format_profile` (:115-147).
**Signature:** `POST gql.twitch.tv/gql` with `{'query': "query { user(login: \"%s\") {...} }" % username}`; headers `{'Client-ID': CLIENT_ID, ...}`.
**Data Shape:** response gates: HTTP 200 AND no top-level `'errors'` key AND `data.user` non-null; fields consumed: `followers.totalCount`, `roles.isPartner/isAffiliate`, `channel.socialMedias[].url`.

### Decisive source
```python
except (requests.exceptions.ProxyError,
        requests.exceptions.ConnectionError) as e:
    if proxies:
        logger.warning(f"Proxy failed for Twitch, retrying direct: {e}")
        r = requests.post('https://gql.twitch.tv/gql',
                          headers=headers, json={'query': query}, timeout=20)  # NO proxies kwarg
    else:
        raise
...
if 'errors' in data:            # GraphQL 200 ≠ success — must check the body
    return None
```

**Flow:** lowercase/strip username → build query by plain `%s` interpolation (no variables block) → POST via the shared proxy ladder; connection-class failures (proxy down/dead) retry ONCE without the proxy rather than surfacing failure — Twitch's public GQL tolerates direct datacenter traffic, unlike instagram. Response must pass THREE gates before `_format_profile`: status 200, absent `errors[]`, present `data.user`.
**Invariant:** the failover is one-directional and exception-typed: only ProxyError/ConnectionError trigger it (Timeout still returns None — a hung proxy retrying direct would double latency for an endpoint that's probably dead); if NO proxy was configured, re-raise preserves the original error. Checking `errors[]` is mandatory because GraphQL wraps per-field failures in HTTP 200. The Client-ID is Twitch's public web client id — treat as ambient constant, not a secret.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "retrying direct\|'errors' in data\|kimne78kx3ncx6brgo4mv6wki5h1ko" app/scrapers/twitch.py` pins :75-85/:93-95/:23; graph retrieval resolves `Scout.app.scrapers.twitch.scrape_profile`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "twitch gql client-id user login", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate GQL consumption shape and typed single-shot direct-failover for endpoints known to tolerate unproxied traffic; adapt the query/fields; omit the hardcoded client-id assumption where ToS requires your own registered id. Note `%s` string interpolation is injection-safe ONLY because usernames are lowercased/alphanumeric here — use GraphQL variables when porting to user-supplied input.
