<!-- capsule-v2 -->
# Root-important-files census — basename+normpath membership with a workflows-directory carve-out

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a repo-map decide which files are structurally important enough to boost in a page-ranked map, regardless of project language?

## One declarative manifest; matching is basename-at-any-depth for listed names, exact-normpath for paths, plus a .github/workflows/*.yml rule
**Path/Symbol:** `aider/special.py`: `ROOT_IMPORTANT_FILES` (:3-177, ~150 entries across 12 categories), `NORMALIZED_ROOT_IMPORTANT_FILES` set (:181, built once at import via `os.path.normpath`), `is_important(file_path)` (:184), `filter_important_files(file_paths)` (:196).
**Signature:** `is_important` checks TWO things in order: (1) `dir_name == ".github/workflows" and file_name.endswith(".yml")`, (2) normalized full path ∈ set (covers nested entries like `.circleci/config.yml`).
**Data Shape:** the set holds normpath'd strings; note `.github/dependabot.yml` is a listed path while bare `dependabot.yml` also exists as a root name — both match by design.

### Decisive source
```python
def is_important(file_path):
    file_name = os.path.basename(file_path)
    dir_name = os.path.normpath(os.path.dirname(file_path))
    normalized_path = os.path.normpath(file_path)
    # Check for GitHub Actions workflow files
    if dir_name == os.path.normpath(".github/workflows") and file_name.endswith(".yml"):
        return True
    return normalized_path in NORMALIZED_ROOT_IMPORTANT_FILES
```

**Flow:** repomap tags each tracked file with importance weight (`filter_important_files` consumed by RepoMap ranking); consumers treat "important" as a ranking multiplier, never an inclusion gate. EXECUTED BEHAVIOR PROBE this run: `Dockerfile` and `sub/dir/Dockerfile` both True (basename matches at any depth); `.github/workflows/ci.yml` True but `ci.yaml` False (extension is exact); `Readme.md` False (case-sensitive).
**Invariant:** case sensitivity is preserved and a listed basename matches at ANY depth because only full paths are compared exactly — this asymmetry between basenames and paths is the whole grammar.
**Probe:** direct tests executed GREEN this run via repo venv (`python -m pytest tests/basic/test_special.py -q`: **13 passed**): `test_is_important` (:8), `::test_is_important_case_sensitivity` (:46), `::test_is_important_with_paths` (:54), parametrized `::test_is_important_various_files` (:75). Deterministic: `grep -c 'def test' tests/basic/test_special.py` → 5.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "is_important ROOT_IMPORTANT_FILES", limit: 3 });
// rank-1: aider.aider.special.is_important aider/special.py 184-193
```

## Verdict
Adopt the manifest + two-rule matcher verbatim for cross-language repo mapping; extend the manifest per ecosystem. Porters who lowercase everything or glob basenames break the pinned case-sensitivity and depth semantics — keep both exact.
