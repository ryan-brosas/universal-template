<!-- capsule-v2 -->
# URL preparation — which inputs get IDNA-encoded, rejected, requoted, and merged with params?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What does `prepare_url` enforce about scheme/host/IDNA/params before any request is built?

## PreparedRequest.prepare_url
**Path/Symbol:** `src/requests/models.py:PreparedRequest.prepare_url` (:483-563); `_get_idna_encoded_host` (:473-481).
**Signature:** `prepare_url(url: UriType, params: ParamsType) -> None`.

### Decisive source
```python
# Don't do any URL preparation for non-HTTP schemes like `mailto`, `data` etc.
if ":" in url and not url.lower().startswith("http"):
    self.url = url
    return
try:
    scheme, auth, host, port, path, query, fragment = parse_url(url)
except LocationParseError as e:
    raise InvalidURL(*e.args)
if not scheme:
    raise MissingSchema(f"Invalid URL {url!r}: No scheme supplied. Perhaps you meant https://{url}?")
if not host:
    raise InvalidURL(f"Invalid URL {url!r}: No host supplied")
if not unicode_is_ascii(host):
    try:
        host = self._get_idna_encoded_host(host)   # idna.encode(host, uts46=True)
    except UnicodeError:
        raise InvalidURL("URL has an invalid label.")
elif host.startswith(("*", ".")):
    raise InvalidURL("URL has an invalid label.")
...
if enc_params:
    query = f"{query}&{enc_params}" if query else enc_params
url = requote_uri(urlunparse((scheme, netloc, path, "", query, fragment)))
```

**Flow:** bytes→utf8 str, lstrip whitespace → non-http scheme with a colon bypasses ALL preparation verbatim → parse via urllib3.parse_url (LocationParseError→InvalidURL) → MissingSchema without scheme (message suggests https) → InvalidURL without host → non-ASCII host through strict IDNA uts46 (UnicodeError→InvalidURL) while ASCII hosts still reject wildcard `*`/leading-dot labels → netloc rebuilt auth@host:port → empty path coerced to "/" → encoded params appended with `&` or fresh → whole URL requoted.
**Invariant:** The http-scheme carve-out means data:/mailto: URLs skip MissingSchema checks too — but only when they CONTAIN a colon; bare "example.com/foo" fails loudly with the did-you-mean hint. IDNA failure is InvalidURL, never a silent passthrough of raw unicode into the request line. Param encoding reuses `_encode_params` so dicts/lists-of-tuples/str/bytes/readables all behave exactly like body form-encoding.
**Probe:** Direct tests: `tests/test_requests.py::TestRequests::test_invalid_url` parametrized matrix (:102-112: MissingSchema bare-host, InvalidURL `http://*example.com` / `http://.example.com`), `::test_params_are_added_before_fragment` (:163), `::test_params_are_merged_case_sensitive` (:1764); `grep -n 'startswith(("\*", "\."))' src/requests/models.py` → 1 hit (:533).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "prepare_url", limit: 10 });
```
(BM25 thin on bare method name — source method resolves line-exact via `search_code --pattern 'def prepare_url'` → :483-563.)

## Verdict
Adopt validation order and the non-http bypass. Adapt IDNA library choice but keep fail-loud semantics. Omit py2 str/bytes dance beyond bytes-decode.
