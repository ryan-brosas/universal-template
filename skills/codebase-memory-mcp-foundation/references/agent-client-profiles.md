<!-- capsule-v2 -->
# Agent client profiles — how do you onboard 40+ coding agents without 40 bespoke installers?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What table-driven profile fields and stability tiers make agent MCP installation declarative?

## Enum + capability bitmask + stability tier registry
**Path/Symbol:** `src/cli/agent_clients.h` (registry 11–70) + tests/test_agent_clients.c:159–460.
**Signature:** `cbm_agent_client_id_t` enum (QODER…SOURCEGRAPH_CODY) × `CBM_AGENT_CAP_*` bits {MCP, INSTRUCTIONS, SKILL, AGENT, HOOK, PLUGIN} × `cbm_agent_client_stability_t` {STABLE, CONDITIONAL, OPT_IN}.
**Data Shape:** Each profile declares documented config paths, precedence rules, override handling (e.g., Rovo path overrides reject relative & traversal & outside-user-root), and per-capability install/uninstall steps resolved from ONE registry.

### Decisive source
```c
typedef enum {
    CBM_AGENT_CLIENT_QODER = 0, ... CBM_AGENT_CLIENT_PI,
    CBM_AGENT_CLIENT_SOURCEGRAPH_CODY,
    CBM_AGENT_CLIENT_COUNT
} cbm_agent_client_id_t;
enum {
    CBM_AGENT_CAP_MCP = UINT32_C(1) << 0,
    CBM_AGENT_CAP_INSTRUCTIONS = UINT32_C(1) << 1,
    CBM_AGENT_CAP_SKILL = UINT32_C(1) << 2, ...
};
```

**Flow:** installer iterates the stable registry → resolves documented paths with precedence/override validation → applies only capability-flagged steps → uninstall reverses via the same table → conditional/opt-in tiers gate auto-detection.
**Invariant:** Registry order is ABI for tests (`agent_clients_registry_is_stable_and_callback_driven`); every path resolution must pass traversal/outside-root rejection before any write.
**Probe:** `tests/test_agent_clients.c:agent_clients_registry_is_stable_and_callback_driven`, `agent_clients_next_wave_metadata_matches_supported_surfaces`, `agent_clients_rovo_override_rejects_relative_and_traversal_paths`, `agent_clients_resolve_documented_paths_and_precedence`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_agent_client_id_t", limit: 5 });
```

## Verdict
Adopt declarative registries with capability bitmasks for multi-target integrations; adapt the capability set; keep the stability-tier gate — it is what makes auto-onboarding safe.
