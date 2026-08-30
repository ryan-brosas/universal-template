<!-- capsule-v2 -->
# Userconfig extension mapping — how do users teach your indexer a brand-new extension without code changes?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What precedence and failure policy should global-vs-project language mappings follow?

## Project-beats-global, unknown-language fail-open
**Path/Symbol:** `src/discover/userconfig.h` (contract 1–36) + tests/test_userconfig.c:103–144.
**Signature:** `cbm_userconfig_t *cbm_userconfig_load(const char *repo_root);` / `CBMLanguage cbm_userconfig_lookup(const cbm_userconfig_t *cfg, const char *ext);`
**Data Shape:** Sources: global `$XDG_CONFIG_HOME/codebase-memory-mcp/config.json` (fallback `~/.config/...`) vs project `<repo>/.codebase-memory.json`, key `extra_extensions: {".blade.php": "php"}`. Result carries sha256 digests of BOTH consumed files so callers can detect config drift. Language matching case-insensitive; unknown values warn+skip.

### Decisive source
```c
/* Project config wins over global. Unknown language values warn and are
 * skipped (fail-open). Missing files are silently ignored. */
TEST(userconfig_project_wins_over_global) {
    /* Global says .xyz → python; project says .xyz → rust */
    ...
    ASSERT_EQ(cbm_userconfig_lookup(cfg, ".xyz"), CBM_LANG_RUST);
```

**Flow:** load global (missing ok) → load project (missing ok) → merge with project precedence per extension → resolve names to CBMLanguage case-insensitively, skipping unknowns with warnings → record source digests for reproducibility.
**Invariant:** A missing file is never an error; an unknown LANGUAGE is a warning not a failure — but the digest capture means behavior changes are detectable.
**Probe:** `tests/test_userconfig.c:userconfig_project_wins_over_global`, `userconfig_unknown_lang_skipped`, `userconfig_global_via_env`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_userconfig_lookup", limit: 5 });
```

## Verdict
Adopt two-tier merge with digests for any user-extensible mapping; adapt config keys; omit XDG fallback if you have a single config home.
