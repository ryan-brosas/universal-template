<!-- capsule-v2 -->
# dotenv ladder — how do you layer .env resolution with zero third-party deps and real-env-wins?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What candidate order, parse rules, and precedence make a stdlib-only .env loader safe to call from every script?

## Three-candidate .env ladder with no-overwrite semantics
**Path/Symbol:** `scripts/env_loader.py:_candidate_paths` (:31-55), `_parse_line` (:58-75), `_load_file` (:78-94), `load_env` (:97-114), `get_env` (:117-129); module flags `_LOADED`/`_LOADED_FROM` (:27-28). Consumed by `github_api.get_token` (:30-46) and by `pagespeed.py:329`, `entity_checker.py:462`, `link_profile.py:305`, `gsc_checker.py:259`.
**Signature:** `load_env(force: bool = False) -> list[str]`; `get_env(*names: str, default: str = "") -> str`.
**Data Shape:** Stdlib only (`os`, `pathlib`). Candidate order: (1) `Path.cwd()/.env`, (2) `<SKILL_DIR>/.env` where SKILL_DIR = parent of the `scripts/` dir containing this file, (3) `$HOME/.agentic-seo/.env` (HOME or USERPROFILE). `load_env` returns the list of paths that actually contributed ≥1 variable. `get_env` returns the first non-empty (post-strip) value among N names, else `default`.

### Decisive source
```python
key, _, value = line.partition("=")                    # :66  first "=" only
...
if key in os.environ:                                  # :90  real env wins, always
    continue
os.environ[key] = value
...
if _LOADED and not force:                              # :104  idempotent
    return list(_LOADED_FROM)
...
for candidate in _candidate_paths():
    if candidate.is_file() and _load_file(candidate) > 0:   # :109
        loaded_from.append(str(candidate))
```

**Flow:** `_candidate_paths` builds cwd → SKILL_DIR → home in that order, tolerating a missing cwd (OSError swallowed) and a missing HOME/USERPROFILE (home candidate skipped), then dedupes by string path preserving order → `load_env` short-circuits on the module-level `_LOADED` flag unless `force=True` → each existing file is parsed line by line: strip, skip blank/`#`, strip an `export ` prefix, partition on the FIRST `=`, require a non-empty key, strip the value, peel one pair of matching single or double quotes (`value[1:-1]`, only when len ≥ 2) → a key already present in `os.environ` is NEVER overwritten — so real shell env beats every file, and an earlier candidate file beats a later one for the same key → unreadable/non-UTF-8 files return 0 silently (a broken .env must not kill the audit) → `get_env` lazily triggers `load_env()` on first call, then walks its name list returning the first value that survives `.strip()`.
**Invariant:** Precedence is exactly: CLI arg (handled by callers, e.g. `get_token` checks `cli_token` before touching env) > process environment > cwd .env > SKILL_DIR .env > home .env. The no-overwrite check happens per-key against the LIVE `os.environ`, which is what makes both "real env wins" and "earlier file wins" fall out of one line. Quote peeling is symmetric-pair-only: `value[0] == value[-1]` must be the same quote char — a value like `"abc'` keeps its quotes. `get_env` strips before the emptiness test, so whitespace-only values fall through to the next name.
**Probe:** no direct upstream test; content pins executed at pin: `Path.cwd() / ".env"` :34 ×1, `here.parent / ".env"` :40 ×1, `".agentic-seo" / ".env"` :44 ×1, `startswith("export ")` :62 ×1, `line.partition("=")` :66 ×1, `value[1:-1]` :74 ×1, `key in os.environ` :90 ×1, `_LOADED and not force` :104 ×1, `candidate.is_file()` :109 ×1; consumer pin `from env_loader import load_env` inside try/except in github_api.py:37-38 ×1; full suite 34 passed.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"load_env get_env candidate paths dotenv precedence","limit":5}}
```
Not executed this pass — Codebase Memory MCP surface absent in the pass-3 session; seam selected and confirmed by direct full-file read of env_loader.py (132L) plus consumer reads at pin (recorded in verification.md). Execute on revalidation.

## Verdict
Adopt the ladder shape verbatim for any multi-location config-file loader: ordered candidates, per-key live-environment no-overwrite, idempotent module flag, silent skip of unreadable files, lazy trigger from the getter. Adapt the three locations to your product (project dir / install dir / user dir) and the quote/export grammar to your format; omit nothing structural — it is 132 lines of stdlib. Coverage caveat: content-pinned only; the multi-name `get_env("A", "B")` fallback idiom (e.g. PAGESPEED_API_KEY→GOOGLE_API_KEY) is pinned at the four consumer call sites, not in a test.
