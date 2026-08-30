<!-- capsule-v2 -->
# mcp-server-persona — how does an IDE expose itself as a local MCP server without the UI?

**Source:** JetBrains installed distributions (proprietary), PyCharm `launch[].customCommands[stdioMcpServer]` + `plugins/mcpserver/` decisive instance. **Question:** What does shipping "IDE as MCP tool" look like as packaging?

## stdioMcpServer customCommand + mcpserver plugin
**Path/Symbol:** `product-info.json:launch[0].customCommands[3].commands=["stdioMcpServer"]`, `mainClass="com.intellij.mcpserver.stdio.McpStdioRunnerKt"`, `vmOptionsFilePath="bin/mcp-server.vmoptions"`; jars: `plugins/mcpserver/lib/{mcpserver.jar, io.modelcontextprotocol.kotlin.sdk.jar, io.github.oshai.kotlin.logging.jvm.jar, ktor-server-sse-jvm.jar}` appended to `bootClassPathJarNames` with RELATIVE paths (`../plugins/mcpserver/...`).
**Signature:** persona = (subcommand name, dedicated vmoptions, trimmed boot classpath ending in plugin jars, headless main class from the MCP Kotlin SDK).
**Data Shape:** rider ships a sibling `plugins/debuggerMcp` and pycharm's code-provenance has `core.mcp` module — the MCP surface appears at THREE layers: product persona (stdio server), debugger bridge plugin, telemetry sink.

### Decisive source
```json
{"commands": ["stdioMcpServer"],
 "vmOptionsFilePath": "bin/mcp-server.vmoptions",
 "bootClassPathJarNames": ["platform-loader.jar", "...", "../plugins/mcpserver/lib/mcpserver.jar",
   "../plugins/mcpserver/lib/io.modelcontextprotocol.kotlin.sdk.jar",
   "../plugins/mcpserver/lib/ktor-server-sse-jvm.jar"],
 "mainClass": "com.intellij.mcpserver.stdio.McpStdioRunnerKt"}
```

**Flow:** `pycharm.sh stdioMcpServer` → launcher resolves the customCommand → boots headless JVM with only platform-core + mcpserver jars → McpStdioRunnerKt serves Model Context Protocol over stdio (Kotlin official SDK + ktor SSE for transport fallback) → tools proxy into the running IDE instance or operate standalone.
**Invariant:** the MCP server is a BOOT PERSONA of the same distribution — no separate installer; its classpath is a strict subset that still names plugin jars relatively, so the persona breaks loudly (missing main class) rather than silently if plugins are stripped. Dedicated vmoptions file isolates its memory profile.
**Probe:** `python3 -c "import json;l=json.load(open('pycharm/product-info.json'))['launch'][0];m=[c for c in l['customCommands'] if 'stdioMcpServer' in c['commands']][0];print(m['mainClass']);print([b for b in m['bootClassPathJarNames'] if 'mcpserver' in b])"` → main class + 4 relative jar paths.
**Retrieve:** search_graph project jetbrains-pycharm query "MCP server stdio" may hit indexed mcpserver classes under dev/ helpers; packaging facts via the JSON probe.

## Verdict
Adopt: expose a heavyweight app to AI agents by adding a named boot persona (headless main + trimmed classpath + own vmoptions) over the SAME install, using the official MCP SDK as transport. Adapt persona naming. Omit JetBrains tool schemas inside the protocol. Caveat: cross-IDE presence varies; probe each product-info.json rather than assuming.
