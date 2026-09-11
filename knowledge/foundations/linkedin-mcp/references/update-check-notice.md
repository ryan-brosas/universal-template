<!-- capsule-v2 -->
# Update-check middleware — a polite version nudge that can never break a tool call

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you notify users of a stale pinned install without polling on every launch or corrupting tool output?

## Background PyPI check → extra content block
**Path/Symbol:** `linkedin_mcp_server/update_check.py` (:1-270; `_is_source_install` :44, `_check_disabled` :62, cache :88-110, fetch :112-130); middleware appends notice to ToolResult.
**Signature:** Cache `<home>/.linkedin-mcp/update-check.json` `{checked_at, latest}`, TTL 24h, request timeout 2.0s; disable env `LINKEDIN_MCP_CHECK_FOR_UPDATES ∈ {0,false,off,no}`.
**Data Shape:** Notice = EXTRA text content block; structured tool output (`{url, sections}`) untouched.

### Decisive source
```python
def _is_source_install() -> bool:
    """True for any non-index install: local path, editable, or VCS.

    PEP 610 writes ``direct_url.json`` only for installs that did not come
    from a package index, so its mere presence marks a source/editable/VCS
    checkout.
    """
```
Skip ladder: explicit off → CI env → source/dev install (direct_url.json presence OR dev-release version) — uvx@latest users re-resolve anyway and are not the audience.

**Flow:** prime from cache synchronously (no network at startup) → background daily check with 2s timeout → meaningful-behind? (two patches behind triggers; single patch doesn't; current/prerelease-latest don't) → append one gentle text block naming the user's install method's fix (uvx config / docker image / GitHub release link).
**Invariant:** A version check must never break or delay a tool call (all network failures swallowed to debug log); notices ride as additive content so documented output shapes stay stable; audience selection via PEP 610 metadata beats parsing install traces.
**Probe:** `tests/test_update_check.py` pins per-install-method notice text and skip branches (`:69 test_notice_on_two_patches_behind`, `:75 test_no_notice_for_single_patch`, `:93 test_no_notice_for_dev_install`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "update_check _is_source_install prime_from_cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the additive-notice + audience-gated update check for any distributed tool server. Adapt registry URL/cache path. Omit PyPI specifics.
