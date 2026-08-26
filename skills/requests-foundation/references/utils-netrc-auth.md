<!-- capsule-v2 -->
# netrc auth lookup — how are credentials discovered from ~/.netrc and what is silently swallowed?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What file locations, env overrides, and exception posture does get_netrc_auth use?

## utils.get_netrc_auth
**Path/Symbol:** `src/requests/utils.py:get_netrc_auth` (:231-280).
**Signature:** `get_netrc_auth(url: UriType, raise_errors: bool = False) -> tuple[str, str] | None`.
**Data Shape:** Returns (login, password) or None; NETRC_FILES = (".netrc", "_netrc").

### Decisive source
```python
netrc_file = os.environ.get("NETRC")
if netrc_file is not None:
    netrc_locations = (netrc_file,)                  # explicit override wins alone
else:
    netrc_locations = (f"~/{f}" for f in NETRC_FILES)
...
if netrc_path is None:
    return                                           # no file → None (no error)
ri = urlparse(url); host = ri.hostname
try:
    _netrc = netrc(netrc_path).authenticators(host)
    if _netrc and any(_netrc):
        login_i = 0 if _netrc[0] else 1              # account field used as login when login empty
        return (_netrc[login_i] or "", _netrc[2] or "")
except (NetrcParseError, OSError):
    if raise_errors:                                 # default: SILENTLY skip auth
        raise
except (ImportError, AttributeError):
    pass                                             # App Engine hackiness legacy
```

**Flow:** $NETRC env short-circuits to a single location → else `~/.netrc` then `~/_netrc` first-existing → missing file/host or parse failure → None by default (raise_errors=True for callers wanting loudness) → empty-login entries fall back to the account slot.
**Invariant:** Fail-SILENT is deliberate posture: a malformed netrc must not break unrelated requests; only `trust_env` sessions consult this at all. Callers: Session.prepare_request (when neither request nor session auth set) and rebuild_auth on redirects (re-arming stripped Authorization per-host).
**Probe:** Direct tests: `tests/test_utils.py::TestGetNetrcAuth` (:156+: test_works, test_not_vulnerable_to_bad_url_parsing, test_empty_default_credentials_ignored) using NETRC env + tmp files; `grep -n 'os.environ.get("NETRC")' src/requests/utils.py` → 1 hit (:239).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "get_netrc_auth authenticators", limit: 10 });
```

## Verdict
Adopt location precedence and fail-silent default. Adapt to host credential stores keeping an equivalent trust_env gate. Omit App Engine branch outside GAE.
