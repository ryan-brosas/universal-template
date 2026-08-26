<!-- capsule-v2 -->
# SearchableOptions index — how does settings search work without booting the UI?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How is the "search every settings page" index precomputed at build time, and what naming convention binds each index file to its owning plugin/module?

## Connected graph-selected seam
**Path/Symbol:** `<jar root>/{p-<pluginId>,m-<moduleId>}-searchableOptions.json` — e.g. `plugins/mcpserver/lib/mcpserver.jar:p-com.intellij.mcpServer-searchableOptions.json`; `dev.jar:m-intellij.dev.psiViewer-searchableOptions.json`. 206 files across pycharm's jars (193 jars), 164 in webstorm.
**Signature:** NDJSON — one JSON object per line: `{"id":"preferences.keymap","name":"|b|messages.KeyMapBundle|k|keymap.display.name|","entries":[{"hit":"|b|messages.ActionsBundle|k|group.ToolsMenu.text|","path":"ActionManager"}]}`.
**Data Shape:** `id` = configurable id; `name`/`hit` = LAZY i18n references in a three-part encoding: `|b|<bundle-class>|k|<bundle-key>|` — never resolved English strings. Entries carry an optional `path` (settings-tree breadcrumb). One file per plugin (p- prefix) or per content module (m- prefix).

### Decisive source
```json
{"id":"com.intellij.mcpserver.settings",
 "name":"|b|messages.McpServerBundle|k|mcp.server.configurable.name|",
 "entries":[{"hit":"|b|messages.McpServerBundle|k|checkbox.enable.brave.mode.skip.command.execution.confirmations|"}]}
```

**Flow:** build-time extractor walks every Configurable and emits raw bundle-key references → at runtime, search indexes these files per jar → a query hit resolves `|b|…|k|…` through the active LocalizationState so results appear in the CURRENT UI language with zero re-extraction.
**Invariant:** the index stores KEYS not text — shipping resolved strings would freeze English into the artifact and break language packs. The p-/m- filename prefix is how the runtime attributes a hit to a plugin for navigation.
**Probe:** `unzip -p plugins/mcpserver/lib/mcpserver.jar p-com.intellij.mcpServer-searchableOptions.json | head -c 200` → starts `{"id":` with `|b|` refs; cluster census pycharm=206 / webstorm=164 files.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "configurable search settings", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: precomputed settings-search shards per plugin, lazy `|b|bundle|k|key` reference encoding, p-/m- ownership prefixes. Adapt to your host's settings model. Omit the extraction pipeline itself (not shipped in installs).
