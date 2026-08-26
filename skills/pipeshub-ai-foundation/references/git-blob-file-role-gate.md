<!-- capsule-v2 -->
# Git-blob file-role gate — which files deserve fetching, parsing and embedding when all you have is a path (and a misclassification only shows up as a subtly worse graph)?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do you decide index-vs-skip for repository blobs from PATH ONLY — pure functions, no I/O — such that the decision is table-testable and cheap to get right?

## Ordered role cascade + ignore list, called before the blob is ever fetched
**Path/Symbol:** `backend/python/app/modules/parsers/code_parser/file_role.py:classify_file_role/is_ignored_path/should_index_code_file` (L154–193 / L141–151 / L196–201; whole file 201L). Sole consumer: `app/connectors/sources/gitlab/repos.py` :741–795 (role+language stamped onto `CodeFileRecord`, non-indexable paths `continue` BEFORE fetch/queue/stream).
**Signature:** `classify_file_role(file_path: str, file_name: str | None = None) -> FileRole`; `should_index_code_file(file_path, file_name=None) -> tuple[bool, FileRole]`; `FileRole(str, Enum)`: SOURCE/TEST/CONFIG/BUILD/MIGRATION/SCRIPT/TYPE_DEFINITION/GENERATED.
**Data Shape:** In: repo-relative path (+ optional display name). Out: one enum. `SKIPPED_ROLES = frozenset({GENERATED})` — the ONLY role whose files are skipped by role; every other role still indexes (roles are metadata, not filters).

### Decisive source
```python
def _segments(file_path: str) -> list[str]:
    """Substring matching would classify ``contest/``, ``latest/`` and
    ``protest.py`` as tests, which is why every directory check below compares
    complete segments."""
    return [seg for seg in (file_path or "").replace("\\", "/").split("/") if seg]

def classify_file_role(file_path, file_name=None):
    # An ordered cascade: the first matching rule wins. Order is the design --
    # files legitimately match several rules, and
    # ``tests/fixtures/generated/foo_pb2.py`` must land on exactly one.
    if dirs & _GENERATED_DIRS or name.endswith(_GENERATED_SUFFIXES) or _GENERATED_RE...:
        return FileRole.GENERATED
    if dirs & _TEST_DIRS or name in _TEST_FILENAMES or any(p.match(name)...):
        return FileRole.TEST
    ...
    # build before config: build.gradle and Dockerfile match both, and the build
    # reading is the more specific one.
```

**Flow:** `is_ignored_path` first (ignored-dir SEGMENTS in any non-final position; lockfiles/`.min.js`/`.map`/`.snap` suffixes; `.git/node_modules/__pycache__/dist/build/target/vendor/…`) → GENERATED (proto/grpc/codegen suffixes `.pb.go`/`_pb2.py`/`.g.dart`/… plus generated dirs) → TEST → MIGRATION → TYPE_DEFINITION (`.d.ts`, `.pyi`, `@types`) → BUILD (Makefile/Dockerfile/Bazel/Gradle + `.github|​.gitlab`-adjacent `workflows` via `_is_ci_workflow` — a plain `src/workflows/` dir stays SOURCE) → CONFIG → SCRIPT → default SOURCE. `should_index_code_file` = NOT ignored AND role ∉ SKIPPED_ROLES.
**Invariant:** (1) Whole-segment matching everywhere — never substring. (2) Cascade order IS load-bearing: GENERATED must beat TEST (`tests/fixtures/generated/foo_pb2.py` lands on exactly one), BUILD beats CONFIG (build.gradle/Dockerfile match both). (3) Ignore ≠ classify: `build/generated/app.js` is ignored outright (whole tree skipped), not merely labelled BUILD. (4) Generated code is skipped because it "is a machine restatement of a schema that is itself indexed" — dropping TESTS from indexing would be wrong; tests are indexed with role=TEST. (5) Pure path logic, zero I/O — the whole cascade is table-testable and safe to call from a git-tree listing where content doesn't exist yet.
**Probe:** `backend/python/tests/unit/modules/parsers/code_parser/test_file_role.py` :17–55 role matrix incl. generated-beats-test (:21), build-beats-config (:39–41); :60–75 segment-not-substring traps (`contest/`, `latest/`, `protest.py`, `greatest_hits.py`, plain `workflows/` dirs); :77–97 ignored-path matrix + negatives; :100–106 should_index gate; :109–112 directory-named-build ignored-not-labelled.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "classify_file_role" --detail ids
```

## Verdict
Adopt verbatim for any repo-ingestion pipeline (connector crawlers, monorepo indexers): the segment rule, the cascade order, and the ignore≠classify split are the three things porters get wrong. Adapt the dir/suffix tables to your ecosystem (tables are data — extend freely). Omit nothing; every rule class has direct parametrized coverage upstream. Coverage caveat: none material.
