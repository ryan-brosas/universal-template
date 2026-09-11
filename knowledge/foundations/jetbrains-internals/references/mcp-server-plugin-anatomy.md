<!-- capsule-v2 -->
# MCP server plugin anatomy — how is an IDE exposed as an MCP server with per-domain toolsets?

**Source:** JetBrains IDE distributions (proprietary distribution; plugin.xml Apache-2.0-marked); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does a host app expose its internal capabilities as MCP tools through a plugin, and what EP taxonomy keeps toolsets modular and filterable?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/plugins/mcpserver/lib/mcpserver.jar:META-INF/plugin.xml` + `modules/intellij.mcpserver.{terminal,vcs,terminal.frontend}.jar`.
**Signature:** 7 EPs under `com.intellij`: `mcpToolsProvider`, `mcpToolFilterProvider`, `mcpToolset`, `mcpProjectPathCustomizer`, `mcpManagedSessionSupport`, `elicitationProvider`, `projectDependenciesProvider` (all `dynamic="true"`). Boot: `<appStarter id="mcpServer" implementation="com.intellij.mcpserver.McpServerHeadlessStarter" internal="true"/>`.
**Data Shape:** `<content namespace="jetbrains">` embeds per-module CDATA descriptors; each module declares `<mcpServer.mcpToolset implementation="…toolsets.general.{Execution,Analysis,File,Formatting,Universal,Read,Patch,Search,CodeInsight,Refactoring}Toolset"/>`; tool filtering via 4 stacked `mcpToolFilterProvider`s (DisallowList/Settings/RegistryKey/IndividualRegistryKey); registryKeys `mcp.server.tools.filter` (glob grammar `-*,+com.intellij.mcpserver.toolsets.general.*,-*.read_file`), `mcp.server.structured.tool.output`, `mcp.server.progress.notification.interval.ms=1000`.

### Decisive source
```xml
<extensionPoint name="mcpToolset" interface="com.intellij.mcpserver.McpToolset" dynamic="true"/>
<appStarter id="mcpServer" implementation="com.intellij.mcpserver.McpServerHeadlessStarter" internal="true"/>
<mcpServer.mcpToolFilterProvider implementation="…DisallowListBasedMcpToolFilterProvider"/>
<mcpServer.mcpToolFilterProvider implementation="…RegistryKeyMcpToolFilterProvider"/>
<registryKey defaultValue="" description="Filter for MCP tools, like -*,+…general.*,-*.read_file"
             key="mcp.server.tools.filter"/>
```

**Flow:** headless starter boots the IDE without UI → toolsets register their tools → filter providers stack to compute the visible set (disallow-list from settings, then registry-key glob, then per-key) → structured-output registryKey toggles schema emission → progress keep-alives throttled at 1000ms.
**Invariant:** tools are grouped by DOMAIN (execution vs analysis vs file vs patch) so a host can expose a strict subset; filtering is a STACK of providers, each independently replaceable — a porter must keep the layering, not collapse to one filter.
**Probe:** `unzip -p plugins/mcpserver/lib/mcpserver.jar META-INF/plugin.xml | grep -c 'mcpToolset implementation'` → 10 general toolsets + terminal/vcs modules; `grep -o 'key="mcp.server.tools.filter"'`.
**Coverage caveat:** manifest plane; direct extraction. The Kotlin MCP SDK + ktor jars ride as sibling libs (io.modelcontextprotocol.kotlin.sdk.jar, ktor-server-sse-jvm.jar) — pass-2's mcp-server-persona pinned the boot persona; this capsule pins the toolset/filter EP taxonomy.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "mcp server toolset filter", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: domain-split toolset EPs + stacked filter providers + glob filter grammar + registry-gated structured output + headless appStarter. Adapt tool implementations to your host. Omit the SDK/ktor internals.
