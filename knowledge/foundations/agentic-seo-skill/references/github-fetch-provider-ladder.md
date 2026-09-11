<!-- capsule-v2 -->
# github-fetch provider ladder — how does one call site get GitHub data over REST *and* the `gh` CLI without losing error context?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** When a host may or may not have a token and may or may not have `gh` installed, in what ORDER do you attempt transports, and what must survive total failure?

## Unified accessor with auth-shaped attempt ordering
**Path/Symbol:** `scripts/github_api.py:fetch_json` (:352-434); helpers `auth_context` (:108-117), `rest_json`, `gh_api_json`.
**Signature:** `fetch_json(path, token="", method="GET", params=None, body=None, accept="", timeout=20, retries=2, provider="auto") -> dict`.
**Data Shape:** Returns `{"data": <parsed JSON>, "status": int, "rate_limit": {...}}` (the `gh` branch fabricates `status: 200, rate_limit: {}`). Raises `GitHubAPIError` on invalid mode, exhausted attempts.

### Decisive source
```python
attempts = []
if ctx["token_present"]:
    attempts.append(("api(token)", lambda: try_rest(token)))
    if ctx["gh_available"]:
        attempts.append(("gh", try_gh))
    attempts.append(("api(public)", lambda: try_rest("")))
else:
    if ctx["gh_authenticated"]:
        attempts.append(("gh", try_gh))
        attempts.append(("api(public)", lambda: try_rest("")))
    else:
        attempts.append(("api(public)", lambda: try_rest("")))
        if ctx["gh_available"]:
            attempts.append(("gh", try_gh))

for label, fn in attempts:
    try:
        return fn()
    except GitHubAPIError as exc:
        errors.append(f"{label}: {exc}")
        continue

detail = " | ".join(errors) if errors else "No provider attempts available."
raise GitHubAPIError(f"All provider attempts failed. {detail}")   # :413-434
```

**Flow:** validate mode ∈ {auto, api, gh} → `api`=REST only; `gh`=CLI only; `auto`=order by `auth_context`: token present ⇒ [api(token), gh?, api(public)], else gh-authenticated ⇒ [gh, api(public)], else [api(public), gh?] → run attempts sequentially, first success returns → each `GitHubAPIError` is caught, LABELED with its transport (`"api(token): …"`), accumulated, and merged into one final error joined by `" | "`.
**Invariant:** Fallback never silently discards why earlier transports failed — the combined error carries every labeled attempt. Only `GitHubAPIError` triggers fallback (network exceptions are pre-wrapped by `rest_json`), so a bug that raises something else surfaces instead of being absorbed.
**Probe:** repo-owned suite green at pin: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` → 34 passed (executed @69199160); content pins via grep on `scripts/github_api.py`: `attempts\.append` = 7 (:413-424), `All provider attempts failed` = 1 (:434), `"api\(token\)"` = 1 (:413).
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"fetch_json unified provider attempts fallback","limit":5}}
```
Executed live: resolves `scripts/github_api.py:fetch_json` (:352-434) rank-1 alongside `gh_api_json`/`rest_json`.

## Verdict
Adopt the labeled-attempt-list fallback and the auth-context-derived ordering verbatim for any dual-transport API client; adapt the transport pair (REST+CLI) and the fabricated `status:200` for `gh` to your host's providers; omit the hardcoded `api.github.com` base only if you keep `_build_url`'s absolute-URL passthrough. Coverage caveat: no upstream unit test imports `github_api` directly — behavior pinned by executed content probes + the passing suite; fan-in evidence = inbound trace of `gh_api_json` (12 caller scripts).
