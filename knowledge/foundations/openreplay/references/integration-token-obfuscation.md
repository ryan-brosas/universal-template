<!-- capsule-v2 -->
# Issue-tracking integration token obfuscation — how are Jira/GitHub tokens displayed and updated without round-tripping secrets?

**Source:** openreplay AGPL-3.0 (api MIT portions) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What read/update contract keeps `oauth_authentication.token` out of API responses while still allowing updates?

## keep-last-4 stars on read; obfuscate flag guards re-write
**Path/Symbol:** `api/chalicelib/core/issue_tracking/base.py` — abstract contract (`get_obfuscated`, `update(changes, obfuscate=False)`: :41–55, storage table `public.oauth_authentication` :30–39); `jira_cloud.py` — local `obfuscate_string` (:9–11: `"*"*(len-4)+last4`) + `get_obfuscated` (:63–69); `github.py` — `helper.obfuscate(text, keep_last=4)` variant (:23–29); dispatcher `integrations_manager.get_integration` (:30–45: SUPPORTED_TOOLS gate, default-integration fallback, for_delete branch).
**Signature:** `get_obfuscated() -> dict | None`; `update(changes, obfuscate=False)`.
**Data Shape:** response token = stars except final 4 chars; UPDATE ... RETURNING token re-obfuscated only when `obfuscate=True` (i.e. the client echoed back a masked value).

### Decisive source
```python
def obfuscate_string(string):
    return "*" * (len(string) - 4) + string[-4:]
...
def update(self, changes, obfuscate=False):
    ...
    w = helper.dict_to_camel_case(cur.fetchone())
    if w and w.get("token") and obfuscate:
        w["token"] = helper.obfuscate(w["token"])
```

**Flow:** GET paths always serve `get_obfuscated()` → PUT with unchanged (starred) token sets `obfuscate=True` so the server detects the mask pattern and skips persisting it; PUT with a fresh secret persists verbatim then returns masked form. Manager resolves provider by stored rows (github EXISTS / jira EXISTS) when tool unspecified.
**Invariant:** The starred value must never be written back as a real token; length-preserving stars mean equality-with-stars is detectable but must be handled via the explicit flag, not string comparison.
**Probe:** `grep -c 'obfuscate=False' api/chalicelib/core/issue_tracking/jira_cloud.py` → `2`; `grep -c 'SUPPORTED_TOOLS' api/chalicelib/core/issue_tracking/integrations_manager.py` → `3`. Direct tests: none upstream for integrations module (grep-pinned caveat).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "obfuscate_string get_obfuscated oauth_authentication jira github", limit: 10 });
```

## Verdict
Adopt masked-read/flag-guarded-write. Adapt to your secret store. Omit provider auto-detect if single-tool.
