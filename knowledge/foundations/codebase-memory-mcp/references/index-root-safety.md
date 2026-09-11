<!-- capsule-v2 -->
# Index root safety — how do you stop an agent from asking you to index `/` or escape via symlinks?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What root-acceptance policy gates index_repository, and what escapes are tested?

## Overbroad-root refusal + CBM_ALLOWED_ROOT allowlist + junction/symlink escape rejection
**Path/Symbol:** `src/mcp/mcp.c` repo_path validation + tests/test_mcp.c:10729 (`mcp_path_within_root_rejects_escape`), 10912 (`index_repository_refuses_overbroad_roots_by_default`), 10943 (`honors_allowed_root`), 10840–10911 (option-like & cmd-metacharacter rejections for base_branch/project_root).
**Signature:** path containment check before any indexing; env `CBM_ALLOWED_ROOT` narrows acceptance; filesystem root NEVER overridable.
**Data Shape:** `/etc` ⇒ "too broad" error; `/` ⇒ "cannot be indexed" unconditionally; Windows junction pointing outside root ⇒ rejected (with native-backslash fixture note); base_branch values starting with `-` or containing cmd metacharacters rejected.

### Decisive source
```c
/* A top-level system tree: refused on breadth, with no configuration. */
char *resp = cbm_mcp_handle_tool(srv, "index_repository", "{\"repo_path\":\"/etc\"}");
ASSERT_TRUE(strstr(resp, "too broad") != NULL);
/* The filesystem root is refused outright and is never overridable. */
ASSERT_TRUE(strstr(resp, "cannot be indexed") != NULL);
```

**Flow:** parse repo_path → canonicalize → breadth check → allowed-root gate → containment proof (realpath, junction-aware) → metachar scan on VCS args → proceed.
**Invariant:** Some refusals must be non-overridable (`/`); option-like strings are injection attempts even in "branch name" fields.
**Probe:** the six named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "path_within_root", limit: 5 });
```

## Verdict
Adopt layered root gates with at least one absolute refusal; adapt platform link semantics; validate every field that reaches a shell or VCS CLI.
