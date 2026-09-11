<!-- capsule-v2 -->
# SSRF-safe bounded download primitive

## Source / Question
`pydantic_ai_slim/pydantic_ai/_ssrf.py` — How does pydantic-ai download a URL safely (SSRF protection + bounded body) so a porter can reuse the primitive without re-deriving the security ladder?

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_ssrf.py` — `safe_download` (477–608), `validate_and_resolve_url` (341–388), `is_private_ip` (211–225), `is_cloud_metadata_ip` (194–208), `_embedded_ipv4s` (151–191), `_read_capped_body` (644–674), `_read_gzip_body` (686–729), `_keeps_credentials` (458–474), `resolve_redirect_url` (391–428).

## Signature
```python
async def safe_download(
    url: str,
    allow_local: bool = False,
    max_redirects: int = 10,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
    max_bytes: int | None = None,
) -> httpx.Response
```

## Data Shape
`ResolvedUrl` dataclass: `resolved_ip: str`, `hostname: str`, `port: int`, `is_https: bool`, `path: str`. `_PRIVATE_NETWORKS` tuple of IPv4/IPv6 networks; `_CLOUD_METADATA_IPV4/IPV6` frozensets; `_SENSITIVE_HEADERS = ('authorization','cookie','proxy-authorization')`; `_BOUNDED_ACCEPT_ENCODING = 'identity, gzip'`.

## Decisive source
The core loop (534–608): each hop re-validates + re-resolves the current URL, checks domain lists, builds a URL with the **resolved IP** (not the hostname), sets `Host` to the original hostname (with non-default port, IPv6 bracketed), sets `sni_hostname` for HTTPS, and manually follows redirects (`follow_redirects=False, stream=True`). On redirect it strips `_SENSITIVE_HEADERS` when `_keeps_credentials(prev, cur)` is False. Bounded reads stream `aiter_raw` and cap both the encoded wire total AND decoded output (gzip via `zlib.decompressobj` with `max_length`).

## Flow / Invariant
1. **Protocol gate first**: `extract_host_and_port` calls `validate_url_protocol` before parsing — only http/https.
2. **Hostname normalization**: `hostname.rstrip('.')` (FQDN trailing dot) + urlparse lowercases — so `169.254.169.254.` can't bypass exact-match domain lists or the IP-literal fast path.
3. **Resolve-then-validate every hop**: DNS → for each IP, cloud-metadata is ALWAYS blocked (even `allow_local=True`); private IP blocked unless `allow_local`. Redirects re-run this per hop (prevents redirect-bypass).
4. **Transition-embedding defense**: `_embedded_ipv4s` decodes IPv4-mapped/-compatible, 6to4, NAT64 (RFC 6052/8215 prefix tables), ISATAP, Teredo (XOR all-ones) so a private/metadata IPv4 can't be smuggled in IPv6 clothing. `exhaustive=False` for private check (avoids misclassifying real public IPv6), `exhaustive=True` only for the metadata guard.
5. **Redirect credential policy**: keep on exact same-origin (scheme+host+port) OR http:80→https:443 same-host upgrade; strip on every other hop (port change, https→http, cross-host). `_keeps_credentials` mirrors httpx's Authorization rule applied to all three sensitive headers.
6. **Bounded download**: only `identity` + `gzip`/`x-gzip` are size-limitable while streaming; `Accept-Encoding: identity, gzip` is sent when `max_bytes` set; other codings rejected. `_read_gzip_body` handles multi-member gzip (zero-padding between members, `unconsumed_tail`/`unused_data` loop), decodes one byte past the cap to distinguish oversized from exact-fit, and raises `httpx.DecodingError` on corrupt/truncated members.

## Probe (direct test)
`tests/test_ssrf.py` (1,558L): `test_private_ips_detected` (:151), `test_ipv4_mapped_ipv6_private` (:180), `test_nat64_metadata_detected` (:266), `test_6to4_metadata_detected` (:281), `test_cloud_metadata_always_blocked` (:529), `test_redirect_to_private_ip_blocked` (:1076), `test_sensitive_headers_across_redirect` (:1461), `test_chained_redirect_keeps_headers_stripped` (:1481), `test_max_bytes_rejects_gzip_bomb_without_materializing_full_decoded_body` (:739), `test_decodes_all_gzip_members` (:831), `test_rejects_truncated_gzip_member` (:856), `test_redirect_followed` (:1053).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'safe_download'` → `_ssrf.safe_download` (477–608) + `TestSafeDownload` (635–1364).

## Verdict
**Adopt** the primitive wholesale — it is a self-contained, well-tested SSRF + bounded-download contract. Adapt `allow_local` semantics and the exact private-range table to your host; the transition-embedding decode ladder is the part a porter would most likely omit and is load-bearing.
