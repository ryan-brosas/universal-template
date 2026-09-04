<!-- capsule-v2 -->
# Agent profile renderers — how do you emit per-agent permission dialects (Claude/Codex/Gemini/…) from one tier model?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What contract guarantees each agent's config dialect gets correct read-only permissions and evidence budgets?

## Dialect table with exact syntax fragments + tiered budgets
**Path/Symbol:** `src/cli/agent_profiles.h` + tests/test_agent_profiles.c:14–60 (dialect expectations), 58–230.
**Signature:** renderer keyed by `cbm_graph_profile_dialect_t` ∈ {CLAUDE, CODEX, GEMINI, QWEN, COPILOT, OPENCODE, KILO, KIRO, JUNIE, QODER, CODEBUDDY, …}.
**Data Shape:** Each dialect row pins: permission fragment (`permissionMode: plan`, `sandbox_mode = "read-only"`, `kind: local`, `"*": deny`…), read tool line (`- Read`, `read`, `read_file`, `Read,Grep,Glob,mcp__…`), grep tool line, and handoff requirements (parent evidence without child MCP; direct tiers fail closed).

### Decisive source
```c
static const direct_dialect_expectation_t direct_dialects[] = {
    {CBM_GRAPH_DIALECT_CLAUDE, "permissionMode: plan", "  - Read\n", "  - Grep\n"},
    {CBM_GRAPH_DIALECT_CODEX, "sandbox_mode = \"read-only\"", "read", "grep"},
    {CBM_GRAPH_DIALECT_GEMINI, "kind: local", "  - read_file\n", "  - grep_search\n"},
    {CBM_GRAPH_DIALEX_OPENCODE..., "  \"*\": deny", "  read: allow", "  grep: allow"},
```
```c
TEST(agent_profiles_tiers_encode_distinct_evidence_budgets)
TEST(agent_profiles_handoff_requires_parent_evidence_without_child_mcp)
TEST(agent_profiles_server_level_dialects_hard_enforce_read_only_tools)
```

**Flow:** pick tier (Scout fast/provisional, Verify default, Auditor bounded-full) → select dialect renderer → emit agent-specific config embedding the tier's tools + budget + coverage-check instruction (`check_index_coverage` before trusting) → unsafe child-MCP formats degrade to explicit parent-handoff text.
**Invariant:** Rendered permissions must be provably read-only per dialect; every direct tier embeds exact path/scope coverage checking with source fallback for flagged gaps.
**Probe:** `tests/test_agent_profiles.c:agent_profiles_direct_dialects_are_coverage_aware_and_read_only`, `agent_profiles_tiers_encode_distinct_evidence_budgets`, `agent_profiles_handoff_only_dialects_fail_closed_for_direct_access`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_graph_dialect_t", limit: 5 });
```

## Verdict
Adopt expectation-table-driven renderers when emitting N config dialects; adapt fragments as agents evolve; never let a dialect silently fall back to another's syntax.
