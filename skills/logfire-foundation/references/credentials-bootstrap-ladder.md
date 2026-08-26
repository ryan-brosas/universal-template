<!-- capsule-v2 -->
# Credentials bootstrap ladder — what happens on first configure() with no token: interactive project creation, creds files, and background validation?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is the resolution order among env token, creds file, and interactive init, and when does validation run synchronously vs in a thread?

## LogfireCredentials + _initialize credentials block
**Path/Symbol:** `logfire/_internal/config.py:LogfireCredentials` (`config.py:1915-2058`) + `_initialize` block (`config.py:1308-1369`).
**Signature:** `load_creds_file(creds_dir) -> Self | None` (raises LogfireConfigError if file EXISTS but invalid); `from_token(token, session, base_url) -> Self | None` (None on unreachable/non-200; only 401 aborts); `initialize_project(client)` — interactive Rich prompts.
**Data Shape:** creds JSON `{token, project_name, project_url, logfire_api_url}` (+ legacy `dashboard_url` remapped via `data.setdefault('project_url', dashboard_url)`).

### Decisive source
```python
try:
    credentials = LogfireCredentials.load_creds_file(self.data_dir)
except Exception:
    # If we have tokens configured by other means, e.g. the env, no need to worry about the creds file.
    if not self.token: raise
    credentials = None

if not self.token and self.send_to_logfire is True and credentials is None:
    # note, we only do this if `send_to_logfire` is explicitly `True`, not 'if-token-present'
    client = LogfireClient.from_url(self.advanced.base_url, self.advanced.server_response_hook)
    credentials = LogfireCredentials.initialize_project(client=client)
    credentials.write_creds_file(self.data_dir)

if credentials is not None:
    self.token = self.token or credentials.token          # env WINS over file
    self.advanced.base_url = self.advanced.base_url or credentials.logfire_api_url
...
if emscripten: check_tokens()
else: Thread(target=check_tokens, name='check_logfire_token').start()
```
Validation semantics (`from_token` docstring): "We continue unless we get a 401. If something is wrong, we'll later store data locally for back-fill." RequestException ⇒ warning "API is unreachable" + None. The eager link print exists because "This may happen some time later in a background thread which can be annoying" — printed_tokens set dedupes against the async path.
**Flow:** explicit token? skip file entirely for auth (still read file for the project URL/link) → no token + send_to_logfile True (strictly not 'if-token-present') → interactive create-project flow writes creds file → merge with env precedence → background per-token validation refreshes/prints links (sync on Emscripten where threads die).
**Invariant:** An invalid-but-present creds file must raise loudly UNLESS an env token exists (graceful migration). 'if-token-present' mode must NEVER prompt — headless containers depend on it. Region-aware base URL comes from token inspection (`get_base_url_from_token`) unless advanced.base_url set.
**Probe:** `tests/test_configure.py::test_initialize_project` family + test_credentials — pins precedence and 401-vs-warn behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "LogfireCredentials load_creds_file from_token initialize_project", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-source ladder (env > creds-file > interactive > none) with explicit-mode-only prompting. Adapt storage format and CLI prompts. Omit region inference if single-endpoint.
