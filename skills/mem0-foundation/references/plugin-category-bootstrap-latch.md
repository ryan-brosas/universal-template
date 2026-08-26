<!-- capsule-v2 -->
# Taxonomy bootstrap latch — how does a background hook replace a hosted project's default taxonomy exactly once per (account, taxonomy) pair?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when a plugin must silently reconfigure a shared server-side resource at session start, what state design makes it once-ever, race-safe, and self-repairing when the taxonomy itself changes?

## setup_coding_categories + auto_setup_categories — fingerprint-keyed apply
**Path/Symbol:** `integrations/mem0-plugin/scripts/setup_coding_categories.py:CODING_CATEGORIES` (38–141) & `_categories_match` (153–166); `integrations/mem0-plugin/scripts/auto_setup_categories.py:categories_fingerprint` (67–80), `apply_categories` (142–152), `_acquire_lock` (158–173).
**Signature:** `categories_fingerprint(categories: list = CODING_CATEGORIES) -> str` (16-hex); `apply_categories(client, proposed: list = CODING_CATEGORIES) -> str` → `"already-configured" | "applied"`.
**Data Shape:** 17 single-key dicts `{name: description}` replacing mem0's consumer default taxonomy (food/hobbies/…) so auto-tagging fits code work. State file `~/.mem0/categories_setup.json`: `{sha256(api_key)[:16]: sha256(taxonomy)[:16]}`; lock file `~/.mem0/categories_setup.lock`.

### Decisive source
```python
def categories_fingerprint(categories: list = CODING_CATEGORIES) -> str:
    """Stable, order-independent 16-hex digest of the category taxonomy.

    Reordering the categories yields the same fingerprint; adding, removing, or
    editing a category changes it (so the taxonomy re-applies on upgrade).
    """
    pairs = sorted(
        (str(key), str(value))
        for entry in categories
        if isinstance(entry, dict)
        for key, value in entry.items()
    )
    payload = json.dumps(pairs, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
```
Latch check is exact equality `state.get(key_fp) == cat_fp` — true only when THIS account already received THIS taxonomy.

**Flow:** SessionStart background run → resolve api key (absent → silent skip) → compute both fingerprints → state hit → return without any API call → else acquire O_CREAT|O_EXCL lock (stale lock older than 120s is stolen and retried once) → lazy-import MemoryClient (ImportError → "venv installing?" retry next session) → fetch `project.get(fields=["custom_categories"])` (non-dict response degrades to None) → `_categories_match(current, proposed)` (key-set equality + strip-equal descriptions, tolerating order and extra API fields) → skip write on match, else `project.update(custom_categories=proposed)` → save state ONLY after success (an API failure skips the save so the next session retries).
**Invariant:** the write is idempotent at three layers — in-memory match check before writing, fingerprint state before contacting the API at all, and exclusive lock across processes — and the state records the TAXONOMY hash, not a boolean, so shipping an edited taxonomy automatically re-applies exactly once per account. The key itself is never persisted (only its sha256 prefix).
**Probe:** `integrations/mem0-plugin/tests/test_auto_setup_categories.py` — fake-client injection pins skip-on-match (`update_calls == []`), apply-on-missing/differing, order-independent fingerprints, opaque key fingerprints ("supersecret" never appears), corrupt-state→`{}`, non-dict get→None; `tests/test_coding_categories.py` pins the taxonomy itself (exactly 17 entries, unique keys, non-empty string descriptions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mem0", query: "categories setup coding custom", limit: 12 });
```
Executed live with `file_pattern: "*_categories.py"`: returns `auto_setup_categories.{categories_fingerprint,fetch_current_categories,apply_categories}`, `setup_coding_categories.{_print_categories,_categories_match,main}` and both test modules.

## Verdict
Adopt the (account-hash → artifact-hash) state map for any "configure remote resource once" hook — it survives new accounts AND upgrades; adopt EXCL-lock-with-stale-steal and success-gated state saves. Adapt the taxonomy contents and the SDK surface to your backend. Omit the coding-specific descriptions. Note for porters: these scripts bootstrap the plugin venv's site-packages onto sys.path at module import, so they run under system python3. Coverage: both files fully indexed (`no_recorded_issue`), whole 236L files read.
