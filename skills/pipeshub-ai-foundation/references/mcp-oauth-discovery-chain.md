<!-- capsule-v2 -->
# MCP OAuth metadata discovery chain — how do you find an MCP server's real authorization/token endpoints when admins and catalog templates get them wrong?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What probe order, URL grammar, and failure posture must a porter copy so discovery finds endpoints that differ from admin-typed/catalog-default URLs (GitHub delegates hosts; Atlassian serves root-only metadata)?

## RFC 9728 → RFC 8414 → OIDC chain over path-inserted well-known candidates
**Path/Symbol:** `backend/python/app/agents/mcp/dcr.py:discover_oauth_metadata/_discover_oauth_metadata_inner/_well_known_candidate_urls/assert_discovery_target_allowed` (L44–185); models `agents/mcp/models.py:DiscoveredOAuthMetadata.supports_dcr/is_usable` (L182–204).
**Signature:** `discover_oauth_metadata(server_base_url: str) -> Optional[DiscoveredOAuthMetadata]`; `_well_known_candidate_urls(base_url: str, well_known_path: str) -> list[str]`; `assert_discovery_target_allowed(url: str) -> None` (async, raises `DiscoveryBlockedError(DCRError)`).
**Data Shape:** `DiscoveredOAuthMetadata{authorization_endpoint?, token_endpoint?, registration_endpoint?, scopes_supported: list, issuer}` — `supports_dcr = bool(registration_endpoint)`, `is_usable = bool(authorization_endpoint AND token_endpoint)` are separate predicates because "can authorize" and "can self-register" are independent capabilities.

### Decisive source
```python
# Module docstring pins the two real-world cases the chain exists for:
#   1. GitHub's MCP server delegates auth to github.com/login/oauth, which
#      shares NO host with api.githubcopilot.com — the protected-resource
#      doc's authorization_servers[] REPLACES the server's own host as
#      candidate issuer list (capped MAX_AS_ISSUER_CANDIDATES = 3).
#   2. Atlassian only serves metadata at the bare authority ROOT.
def _well_known_candidate_urls(base_url, well_known_path):
    # RFC 8414 §3.1: insert the suffix BETWEEN authority and path —
    #   https://mcp.atlassian.com/.well-known/oauth-authorization-server/v1/sse
    # NEVER append after the full URL (.../v1/sse/.well-known/...).
    urls = []
    if path: urls.append(f"{authority}{well_known_path}{path}")   # path-inserted first
    urls.append(f"{authority}{well_known_path}")                  # bare-root fallback

# Best-effort ALL the way down — never raises:
try: return await asyncio.wait_for(_inner(url), timeout=DISCOVERY_TOTAL_TIMEOUT_SECONDS)  # 20s total, 5s per request
except Exception: return None   # callers fall back to the instance's configured URLs
```
SSRF containment: every candidate URL passes `assert_discovery_target_allowed` BEFORE the GET, delegating to the SAME `app.utils.url_fetcher.validate_public_http_url` policy connector fetches use ("exactly one blocked-host list to maintain"). Safe because `httpx.AsyncClient` never follows redirects unless `follow_redirects=True` — never passed here — so one resolve-before-connect check cannot be bypassed by a redirect hop.

**Flow:** probe `/.well-known/oauth-protected-resource` on the MCP server itself → if its `authorization_servers` lists hosts, those become the issuer candidates (else the server's own host) → for each candidate: RFC 8414 path-inserted URL, then bare root, then OIDC `openid-configuration` twin → accept the FIRST dict carrying `authorization_endpoint` or `token_endpoint` → any network error/blocked target/timeout yields `None`, never a raise.
**Invariant:** (1) Discovery result OVERLAYS static config but never silently discards it — a static admin-configured OAuth app is required (not ignored) when the server needs one; discovered endpoints correct templates that point at providers' *direct* OAuth flows. (2) Well-known insertion is between authority and path, plus root fallback — appending after the full path misses Atlassian-shaped servers. (3) Failure is `None`, never an exception; the caller's fallback is the stored `authorizationUrl`/`tokenUrl`. (4) Per-request AND total timeouts both bounded; malicious protected-resource docs listing many AS hosts are capped at 3 candidates × ≤4 requests each. (5) All timestamps timezone-aware UTC (`datetime.now(timezone.utc)` / module-level `utcnow()` helper) — naive datetimes forbidden.
**Probe:** `tests/unit/agents/mcp/test_dcr.py` (473L): Notion-shaped reports dcr_supported :68; **GitHub-shaped delegates to different host WITHOUT dcr** :101; falls back to authority root :136; OIDC fallback :168; all-fail → None :191; network error → None :201; blocked target → None :211; outer timeout → None :227; ignores non-list authorization_servers :237; userinfo stripping :291; rejects loopback/link-local without network :317/:324; registration blocked BEFORE any request :405.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "discover_oauth_metadata _well_known_candidate_urls assert_discovery_target_allowed DiscoveredOAuthMetadata" --detail ids
```

## Verdict
Adopt the three-RFC probe chain with path-inserted well-known grammar, the authorization_servers host-delegation step with its 3-candidate cap, the shared SSRF validator, and the never-raise `None`-on-failure contract with `is_usable`/`supports_dcr` split. Adapt timeout values and the blocked-host list to the host. Omit PipesHub's route wiring (`api/routes/mcp_servers.py`) around it. Coverage: direct dedicated test file exists — no caveat.
