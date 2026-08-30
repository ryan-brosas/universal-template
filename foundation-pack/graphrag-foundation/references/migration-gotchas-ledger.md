<!-- capsule-v2 -->
# Migration-gotchas ledger — how does graphrag turn one-time dependency breakage into reusable, repo-verified repair patterns?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** What is the shape of a "verified fixes for THIS repo" migration ledger, and which pandas 3.0 / numpy 2.x / ruff-preview entries does it encode?

## Key facts
**Path/Symbol:** `.agents/skills/update-deps/references/migration-gotchas.md` — pandas 3.0 `swapaxes`/`array_split` entry (:9-28); CoW `copy=` removal (:30-34); chained-assignment under CoW (:36-40); numpy 2.x alias removals (:42-47); ruff preview RUF069 + ASYNC119 (:49-63); pyright stubs-travel-with-majors (:65-70); General approach (:72-78).
**Signature:** load-on-demand reference — loaded by update-deps SKILL.md step 6 exactly when a bump breaks tests/pyright/ruff with a library API change.
**Data Shape:** each entry = symptom (traceback signature) → mechanism (WHY the API changed) → minimal fix with broken/fixed code pair; every pattern states it was "actually hit and fixed in this codebase" — no speculative entries.

### Decisive source
```python
# migration-gotchas.md :22-28 — THE trap: np.array_split silently changes return TYPE:
# Broken under pandas 3.0
return [pd.DataFrame(fold) for fold in np.array_split(reports, n)]
# Fixed — preserves columns, dtypes, and even fold sizes
return [reports.iloc[indices] for indices in np.array_split(np.arange(len(reports)), n)]
```
```python
# :58-63 — ASYNC119 fix idiom: materialize inside the block, yield AFTER it closes:
with Path.open(path, "r", encoding=enc) as f:
    rows = list(csv.DictReader(f))
for row in rows:
    yield transform(row)
```

**Flow:** bump lands → test/lint failure → read traceback to leaf frame (:74) → match a sibling module's handling (:76) → apply minimal real fix over `# noqa` (:77) → re-run `poe check` + `poe test_unit`. The array_split entry is the deepest: pandas 3.0 removed `DataFrame.swapaxes`, which `np.array_split` used to delegate to — so the SAME call now returns plain ndarrays, and rebuilding frames yields RangeIndex columns whose later `df["col"]` access KeyErrors.
**Invariant:** the ledger only records patterns proven against this repo's own failures and keeps them consistent with sibling code style; fixes preserve observable contracts (columns/dtypes/even-fold-sizes) rather than just silencing errors. The ASYNC119 materialize-then-yield rule exists BECAUSE ruff runs with `preview = true` here — rules that never fire elsewhere are standing constraints.
**Probe:** `grep -nF 'swapaxes' .agents/skills/update-deps/references/migration-gotchas.md` hits :9,:11,:12; `grep -oE 'RUF069|ASYNC119|RUF105' pyproject.toml .agents/skills/update-deps/references/migration-gotchas.md` shows RUF105 only in pyproject (ignore list) while RUF069+ASYNC119 appear as ACTIVE rules documented in the ledger.

## Get live surrounding code
**Retrieve:** Section nodes carry heading text line-exact via search_code:
```
codebase-memory-mcp cli search_code '{"project":"graphrag","pattern":"swapaxes","file-pattern":"*.md"}'
```
rank#1 = the swapaxes section :9-10; Module node carries body matches at :11-13.

## Verdict
Adopt the symptom→mechanism→minimal-fix ledger shape and the specific pandas-3.0 array_split type-change trap (it will recur in ANY pandas 3 port); adapt the library-version specifics to host stack; omit MS-feed-specific notes. Coverage: `no_recorded_issue`; direct-test surface indirect — the fixed patterns keep the unit suites green that other capsules pin.
