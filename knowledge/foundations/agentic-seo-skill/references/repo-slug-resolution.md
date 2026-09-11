<!-- capsule-v2 -->
# repo-slug resolution — how does `--repo` accept URLs, SCP remotes, and slugs, then fall back to git origin?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What identifier forms must normalize to `owner/repo`, and what error does a caller see when nothing resolves?

## Normalization → inference → actionable error ladder
**Path/Symbol:** `scripts/github_api.py:normalize_repo_slug` (:120-137), `infer_repo_from_git` (:140-151), `resolve_repo` (:154-164), `parse_repo_slug` (:167-173).
**Signature:** `normalize_repo_slug(value) -> str` (`""` on failure); `resolve_repo(repo=None, cwd=None) -> str` (raises); `parse_repo_slug(repo) -> (owner, name)` (raises).

### Decisive source
```python
text = re.sub(r"\.git$", "", text)                 # strip .git suffix          :126
if text.startswith("git@github.com:"):
    text = text.split(":", 1)[1]                   # SSH SCP-form remote        :128-129
elif text.startswith(("https://github.com/", "http://github.com/")):
    parsed = urllib.parse.urlparse(text)
    text = parsed.path.strip("/")                  # URL → path                  :130-132
parts = [p for p in text.split("/") if p]
if len(parts) >= 2:
    return f"{parts[0]}/{parts[1]}"                # first two segments win      :134-136
```
```python
inferred = infer_repo_from_git(cwd=cwd)            # git remote get-url origin   :159
if inferred:
    return inferred
raise GitHubAPIError(
    "Could not resolve repository slug. Use --repo owner/repo or run inside a "
    "git repo with origin configured.")            # names BOTH fixes            :162-164
```

**Flow:** explicit value → strip whitespace and trailing `.git` → rewrite `git@github.com:` SCP form or GitHub http(s) URL to its path → keep the FIRST TWO non-empty path segments as `owner/repo` (anything else ⇒ `""`) → else run `git remote get-url origin` (stderr devnull'd, any failure ⇒ `""`) through the same normalizer → still empty ⇒ `GitHubAPIError` whose message names both remedies. `parse_repo_slug` re-normalizes and demands exactly two parts.
**Invariant:** Normalization is total — every branch returns a string, never raises; only `resolve_repo`/`parse_repo_slug` raise, so callers can probe cheaply with `normalize_repo_slug` alone. Extra URL segments (e.g. `/tree/main`) are silently dropped by the two-segment cut.
**Probe:** executed grep pins on `scripts/github_api.py`: `\\.git\$` = 1 (:126), `git@github\.com:` = 1 (:128), `Could not resolve repository slug` = 1 (:163); direct test of the family's local plane `tests/test_link_and_github_depth_scripts.py` executed green (4 passed) at pin.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"normalize repo slug owner slash infer git origin","limit":5}}
```
Executed live: resolves `normalize_repo_slug` (:120-137) rank-1, `infer_repo_from_git` rank-2, `parse_repo_slug` rank-3.

## Verdict
Adopt the form set (slug, `.git` suffix, SCP remote, GitHub URL) and the two-segment cut verbatim; adapt the host list (add GitLab/etc. prefixes as new branches rather than regex soup) and wire your own CLI's flag name into the error text; omit the silent segment-drop if your porter must reject deep URLs loudly instead. Coverage caveat: no upstream unit test imports these helpers directly — behavior pinned by executed content probes; consumers verified via inbound trace (`build_audit`, `audit_release_seo` call sites).
