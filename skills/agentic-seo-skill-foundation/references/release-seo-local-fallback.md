<!-- capsule-v2 -->
# release-seo local fallback — how does a releases audit degrade to git tags and CHANGELOG without faking GitHub data?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** When the GitHub releases endpoint is unavailable, how do you keep auditing cadence while marking every row's provenance?

## API-first, tag-fallback with source markers
**Path/Symbol:** `scripts/repo_release_seo.py:audit_release_seo` (:71-131), `_local_tags` (:25-41), `_release_quality` (:52-68), `_load_changelog` (:44-49).
**Signature:** `audit_release_seo(repo=None, path=".", token="", provider="auto", keywords=None, limit=20) -> dict`.
**Data Shape:** Result keys: `repo, auth_context, summary{score, releases_analyzed, latest_release_age_days, release_notes_with_summary, release_notes_with_keywords}, changelog{present,bytes,release_headings}, releases[], issues[], limitations[]`. Each release row carries `source`: `"github_release"` (default) or `"git_tag"`.

### Decisive source
```python
try:
    resolved_repo = resolve_repo(repo, cwd=path)
    payload = fetch_json(f"/repos/{resolved_repo}/releases", token=token,
                         params={"per_page": min(limit, 100)}, provider=provider)
    releases = payload.get("data") or []
except GitHubAPIError as exc:
    limitations.append(f"GitHub releases unavailable: {exc}")
...
if not releases:
    releases = _local_tags(path, limit=limit)                 # git for-each-ref fallback :86-87
    if releases:
        limitations.append("Using local git tags because GitHub releases were unavailable.")
```
```python
"has_summary": len(body.strip()) >= 120,                      # :62
"has_bullets": bool(re.search(r"^\s*[-*]\s+", body, flags=re.M)),
```

**Flow:** resolve slug → fetch releases (per_page clamped `min(limit,100)`) → on failure record limitation, keep empty list → empty ⇒ run `git for-each-ref --sort=-creatordate --count=N refs/tags`, parse `name\tiso-date` rows with empty bodies and `source:"git_tag"`, append a second limitation → score each row (title = name‖tag_name; keyword substring match over lowercased title+body; ≥120-char body ⇒ has_summary; multiline bullet regex ⇒ has_bullets; draft/prerelease flags) → newest age from parsed ISO dates → issues + additive penalties: no rows −20, newest>180d −15 (warning), <50% rows with summary −10 (info), missing CHANGELOG.md −10 (warning), zero keyword matches info-only (no penalty); floor at 0.
**Invariant:** Provenance is per-row (`source` field) and the degradation is always announced in `limitations[]` — a mixed report never lets a bare tag masquerade as an annotated GitHub release. Local tags have empty `body`, so they legitimately fail the `has_summary` bar instead of inheriting fake notes.
**Probe:** executed grep pins on `scripts/repo_release_seo.py`: `refs/tags` = 1 (:28), `"source": "git_tag"` = 1 (:40), `>= 120` = 1 (:62), `has_bullets` regex = 1 (:63), `stale_releases` = 1 (:104), `with_notes / len\(rows\) < 0\.5` = 2 (:105 issue,:115 score), `missing_changelog` = 1 (:110); repo-owned suite 34 passed @pin.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"audit release seo tags changelog quality","limit":5}}
```
Executed live: resolves all four module functions ranks 1-4 (`_load_changelog`, `_local_tags`, `_release_quality`, `audit_release_seo`).

## Verdict
Adopt the fallback-with-provenance pattern and the additive penalty table verbatim for cadence/release audits; adapt the 120-char summary bar, 180-day staleness window, and penalty magnitudes to your scoring doctrine; omit the git-tag parser only if your host guarantees API access (then keep the limitation channel for partial pages). Coverage caveat: no upstream unit test imports this module — behavior pinned by executed content probes at the listed lines; direct read of the whole 156-line file at pin.
