<!-- capsule-v2 -->
# Env-URL scanner — how do you inventory service endpoints from config files without leaking secrets?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What file types, filters, and exclusions make a config-walking URL scanner safe to expose?

## Multi-format ENV scan with secret filter and discovery-exclusion honor
**Path/Symbol:** `src/pipeline/pass_envscan.c:cbm_scan_project_env_urls_excluded` (567+) + header contract pipeline_internal.h:633–651; tests tests/test_pipeline.c:9139–9230.
**Signature:** `int cbm_scan_project_env_urls_excluded(const char *root_path, cbm_env_binding_t *out, int max_out, char **excluded_dirs, int excluded_count);`
**Data Shape:** Binding = {key[128], value[512], file_path[256]}. Scans Dockerfile (`ENV`/`ARG`), shell exports, `.env`, YAML, TOML, Terraform, `.properties`; only URL-shaped values pass (e.g. `https://api.example.com/api/orders` in, `DB_HOST=localhost` out).

### Decisive source
```c
/* Walks a project directory, scans config files ... for environment variable
 * assignments where the value is a URL. Filters out secrets.
 * ... The _excluded variant honors discovery exclusions for consistency with
 * the pkgmap/path-alias walks (#792) ... */
TEST(envscan_dockerfile_env_urls) {
    ... "ENV ORDER_URL=https://api.example.com/api/orders\n"
        "ENV DB_HOST=localhost\n" ...
    ASSERT_NOT_NULL(find_binding_by_key(bindings, count, "ORDER_URL"));
    ASSERT_TRUE(find_binding_by_key(bindings, count, "DB_HOST") == NULL);
```

**Flow:** walk root honoring the same exclusion lists as file discovery → per matching file run format-specific regexes (≤5 groups) → capture KEY=URL pairs → secret-value heuristics drop credentials → cap results at max_out.
**Invariant:** Exclusion parity with the main walker (#792) — a scanner that sees MORE than the indexer produces confusing ghosts; non-URL values must never surface.
**Probe:** `tests/test_pipeline.c:envscan_dockerfile_env_urls`, `envscan_shell_env_urls`, `envscan_env_file_urls`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_scan_project_env_urls", limit: 5 });
```

## Verdict
Adopt exclusion-parity walkers with value-shape filtering for any config mining; adapt regexes per format; note the plain variant currently has NO production caller — treat this as a library seam.
