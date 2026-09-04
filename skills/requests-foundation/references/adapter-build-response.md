<!-- capsule-v2 -->
# Response construction — which urllib3 response fields map onto requests.Response, and what context gets attached?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What does HTTPAdapter.build_response copy vs attach, and why keep `response.connection`?

## HTTPAdapter.build_response
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.build_response` (:365-401).
**Signature:** `build_response(req: PreparedRequest, resp) -> Response`.

### Decisive source
```python
response = Response()
response.status_code = getattr(resp, "status", None)      # tolerate status-less mocks
response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))
response.encoding = get_encoding_from_headers(response.headers)
response.raw = resp                                       # LIVE stream handle kept
response.reason = response.raw.reason
...
extract_cookies_to_jar(response.cookies, req, resp)
response.request = req
response.connection = self                                # adapter back-reference
```

**Flow:** fresh Response ← status/headers/reason from urllib3 resp (getattr-defaulted so test doubles survive) → encoding derived ONCE from headers (`get_encoding_from_headers`: charset param → ISO-8859-1 for text/* → utf-8 for application/json → None) → raw kept unconsumed → cookies extracted → request+connection attached.
**Invariant:** `.raw` retention is the streaming contract; `response.connection = self` is what lets `HTTPDigestAuth.handle_401` resend via `r.connection.send(prep)` — porters who drop it break digest auth's self-resend. Encoding precedence lives here, NOT at text-access time: charset header beats text-default beats json-utf8 beats chardet-at-text-time. bytes URLs decoded to str once.
**Probe:** Direct tests: `tests/test_lowlevel.py::test_digestauth_401_count_reset_on_redirect` (:127), `::test_digestauth_401_only_sent_once` (:192), `::test_digestauth_only_on_4xx` (:238) — direct pinning of the num_401_calls/4xx-gate contract; `grep -n "response.connection = self" src/requests/adapters.py` → 1 hit (:399).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "build_response CaseInsensitiveDict extract_cookies", limit: 10 });
```

## Verdict
Adopt field-mapping defaults (None-status tolerance) and the connection back-reference requirement. Adapt encoding ladder to host i18n policy but keep header-first ordering. Omit nothing else.
