<!-- capsule-v2 -->
# Cloud profile plane — how do you paginate an item-capped list API, resolve names fail-loud, and sync local cookies without closing Chrome?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What contract makes cloud-profile listing, name→id resolution, and local-cookie sync safe to call from agent code that cannot interactively disambiguate?

## Paginated listing + exact-name resolver + profile-use sync shell-out
**Path/Symbol:** `src/browser_harness/admin.py:list_cloud_profiles` (:586-613), `_resolve_profile_name` (:616-623), `sync_local_profile` (:666-710), `start_remote_daemon` name/id guard (:641-644).
**Signature:** `list_cloud_profiles() -> [{id, name, userId, cookieDomains, lastUsedAt}]`; `_resolve_profile_name(profile_name) -> uuid`; `sync_local_profile(profile_name, browser=None, cloud_profile_id=None, include_domains=None, exclude_domains=None) -> uuid`.
**Data Shape:** API caps `pageSize` at 100; each item enriched by a per-id `GET /profiles/{id}` detail call; `cookieDomains` is the cheap "how much is logged in" summary (`len()` it, don't ship per-cookie detail).

### Decisive source
```python
if isinstance(listing, dict) and len(out) >= listing.get("totalItems", len(out)):
    break
page += 1
```
```python
if len(matches) > 1:
    raise RuntimeError(f"{len(matches)} cloud profiles named {profile_name!r} -- pass profileId=<uuid> instead")
```

**Flow:** List loop fetches `?pageSize=100&pageNumber=N`, enriches every item with its detail GET, and stops on EITHER empty items OR `len(out) >= totalItems`. Name resolution requires EXACTLY one match — zero raises with the recovery instruction ("call list_cloud_profiles() or sync_local_profile() first"), duplicates raise pointing at the profileId escape hatch; `start_remote_daemon` rejects passing both name and id. Sync shells out to `profile-use sync` (fails loud if not installed), injects `BROWSER_USE_API_KEY` into the CHILD env only, streams child stdout/stderr through, applies exclude-domains BEFORE include so exclude wins overlap, and recovers the UUID from stdout regex `Profile created:\s+([0-9a-f-]{36})` — or short-circuits to the known id when `--cloud-profile-id` was passed (the tool then prints a different line).
**Invariant:** Ambiguity must raise, never guess: duplicate names are unresolvable client-side and the error names the escape hatch. Pagination trusts totalItems over "did the last page look full" because the API enforces pageSize≤100. The tool copies the profile dir to a temp before syncing so Chrome can stay open — the Python layer never touches the live profile.
**Probe:** Executed against pinned source with stubbed `_browser_use`: dup-name → `RuntimeError("2 cloud profiles named 'work' -- pass profileId=<uuid> instead")`; zero-match → recovery-instruction error; page1={2 items,totalItems=2} + page2-with-items → exactly 1 page fetched, 2 detail GETs, ids `[x,y]` (early termination proven — page 2 was never requested despite having items). No direct unit test covers this plane — coverage caveat; anchors verified at source :586-710.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "cloud profiles paginate resolve sync", file_pattern: "*.py", limit: 10 });
```

## Verdict
Adopt the two-condition pagination break, raise-don't-guess name resolution with escape-hatch errors, and child-env-only secret injection for CLI shelling. Adapt the pageSize cap, stdout UUID regex, and `profile-use` CLI shape to your provider. Omit Browser Use specifics (`/profiles`, `/browsers` routes) unless porting the whole cloud plane.
