<!-- capsule-v2 -->
# Home config templates — `$DSH_HOME` settings + MCP servers

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a DSH template provide copy-ready `$DSH_HOME` config templates for the default agent preset and MCP servers, without ever committing secrets?

## `$DSH_HOME` config templates
**Path/Symbol:** `.dsh/home/settings.yaml` (whole file, 32 lines) — `agent-presets.default` (13–14), the commented model/provider/agent-loop blocks; `.dsh/home/mcp.yaml` (whole file, 45 lines) — `mcp.servers` (19–45) with `codebase-memory`, `exa`, `context7`, `deepwiki`.
**Signature:** copy to `$DSH_HOME/settings.yaml` (~/.dsh/settings.yaml) and `$DSH_HOME/mcp.yaml`; DSH reads them at boot. Secrets go in `$DSH_HOME/.credentials.yaml` or env vars, never committed.
**Data Shape:** `settings.yaml` sets `agent-presets.default: fabric` (adds Fabric disciplines when `dsh-fabric` is installed); commented blocks show `agent-default-model`, `agent-loop.maxParallelToolCalls`, and an `llm-pi-ai.providers` schema. `mcp.yaml` declares `mcp.servers` each with `command`, `args`, optional `env`, `description`, `transport: stdio`.

### Decisive source
```yaml
# settings.yaml — copy to $DSH_HOME/settings.yaml and adapt.
agent-presets:
  default: fabric
# agent-default-model:
#   provider: crof
#   model: deepseek-v4-pro-0813
# agent-loop:
#   maxParallelToolCalls: 20
```
```yaml
# mcp.yaml — copy to $DSH_HOME/mcp.yaml and adapt.
mcp:
  servers:
    codebase-memory:
      command: codebase-memory-mcp
      args: []
      description: "Codebase Memory MCP for repository navigation and indexing"
      transport: stdio
    exa:
      command: npx
      args: ["-y", "exa-mcp-server"]
      env: { EXA_API_KEY: "${EXA_API_KEY}" }
      description: "Real-time web search and web crawl (Exa)"
      transport: stdio
    context7:
      command: npx
      args: ["-y", "@upstash/context7-mcp@latest"]
      description: "Up-to-date documentation for libraries and frameworks (Context7)"
      transport: stdio
```

**Flow:** (1) copy `settings.yaml` to `$DSH_HOME` and set the default agent preset (e.g. `fabric`); (2) copy `mcp.yaml` to `$DSH_HOME` and declare MCP servers (each with command/args/env/transport); (3) put real API keys in `$DSH_HOME/.credentials.yaml` or env vars, never in the committed template; (4) confirm a server is registered and connected before relying on its tools.

**Invariant:** the committed templates never contain real secrets (only `${ENV}` references); DSH reads these at boot; MCP servers are declared in `mcp.servers` with `transport: stdio`; a server must be confirmed connected before use.

**Probe:** no direct test file exists. Verified by direct source read (both files indexed `no_recorded_issue`, `freshness: not_tracked`). `node scripts/check.mjs` verifies both files exist.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "settings.yaml agent-presets mcp.yaml servers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the copy-ready `$DSH_HOME` template pattern (settings + MCP), the `agent-presets.default` + `mcp.servers` shape, and the env-var-only secrets discipline. Adapt the model/provider config and the MCP server list to the host. Omit servers the host does not install (e.g. `exa` without `EXA_API_KEY`).
