<!-- capsule-v2 -->
# gh-auth exit-zero trap — why must `gh auth status` output be parsed as text even when it exits 0?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** How does a script decide token vs `gh`-session vs anonymous mode, and what breaks if you trust the CLI's exit code?

## Text-parsed auth probe with module-level cache
**Path/Symbol:** `scripts/github_api.py:gh_auth_details` (:63-105), `auth_context` (:108-117), `get_token` (:32-45); cache `_GH_AUTH_CACHE` (:20).
**Signature:** `gh_auth_details(force_refresh=False) -> {"available": bool, "authenticated": bool, "raw": str}`; `auth_context(token="") -> {"token_present","gh_available","gh_authenticated","mode"}`; `get_token(cli_token=None) -> str`.
**Data Shape:** `mode ∈ {"token", "gh", "unauthenticated"}`; token ladder returns `""` (never None) so callers branch on falsy.

### Decisive source
```python
# `gh auth status` may exit 0 even with invalid token, so parse output text.  # :67
result = subprocess.run(["gh", "auth", "status", "-h", "github.com"],
                        capture_output=True, text=True, check=False, timeout=12)
text = (result.stdout or "") + "\n" + (result.stderr or "")
lower = text.lower()
authenticated = (
    "logged in to github.com" in lower
    and "failed to log in" not in lower
    and "not logged into" not in lower
    and "token is invalid" not in lower
)                                                                          # :93-98
```

**Flow:** `get_token`: CLI override `.strip()` → best-effort `env_loader.load_env()` (bare `except Exception: pass`) → env `GITHUB_TOKEN` then `GH_TOKEN`, stripped → `""`. `gh_auth_details`: cached in module global (`force_refresh` bypasses) → `gh --version` availability probe → run status command, merge stdout+stderr, lowercase, require the success phrase AND absence of all three failure phrases → cache. `auth_context` folds both into the mode trichotomy consumed by `fetch_json`'s provider ladder.
**Invariant:** Exit code is NOT an authenticity signal here — the positive phrase must be present AND negative phrases absent, because `gh` reports invalid/expired tokens with exit 0. The cache means one process-wide decision: force_refresh exists precisely because tests/retries may need re-probing after `gh auth login`.
**Probe:** executed grep pins on `scripts/github_api.py`: `"logged in to github.com"` = 1 (:94), `token is invalid` = 1 (:97), `_GH_AUTH_CACHE` = 6 (:20,:69,:70,:71,:79,:104); repo-owned suite 34 passed @pin.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"gh auth status authenticated token invalid cache","limit":5}}
```
Executed live: resolves `gh_auth_details`/`auth_context` in `scripts/github_api.py`.

## Verdict
Adopt the phrase-AND-negation parse and the three-way mode context verbatim for any CLI-delegated credential probe; adapt the phrases to your CLI's actual wording (they are versioned UI text — pin them behind constants at port time); omit the `.env` auto-load only if your host forbids dotenv side effects (the bare except makes it fail-open by design). Coverage caveat: no upstream unit test exercises these functions; behavior pinned by executed content probes at :94/:97 and direct read of :32-117.
