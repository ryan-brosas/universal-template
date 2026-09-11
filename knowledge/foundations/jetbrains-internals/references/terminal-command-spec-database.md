<!-- capsule-v2 -->
# Terminal command spec database — how does the IDE know every CLI's flags without shipping a shell?

**Source:** JetBrains IDE distributions (proprietary distribution; platform XML headers marked Apache-2.0); study/reference use only; Codebase Memory `jetbrains-pycharm` (code plane only). **Question:** How do you ship autocomplete for hundreds of external CLIs as static data, and what is the two-level index/lazy-load contract a porter must reproduce?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/plugins/terminal/lib/terminal-completion-db-with-extensions.jar` → `completionSpecs/all_commands.json` + per-command spec files (1,436 entries).
**Signature:** `META-INF/completion-specs.xml` → `<extensions defaultExtensionNs="org.jetbrains.plugins.terminal"><commandSpecs path="completionSpecs/all_commands.json"/></extensions>`.
**Data Shape:** `all_commands.json` = flat array of 689 top-level commands `{names:[...], description?, loadSpec}` — deliberately tiny so the whole index stays in memory. Each `loadSpec` names a second file (`completionSpecs/<cmd>.json`, or versioned dirs like `aws/`, `az/2.53.0/`, `gcloud/`) holding the full tree: recursive `subcommands[]` + `options[]` with `args[].templates:["filepaths"]`, `suggestions:[{names}]`, `default:"undefined"`. Largest payloads: gcloud/compute 4.5MB, az/network 1.9MB, aws/ec2 1.6MB.

### Decisive source
```xml
<extensions defaultExtensionNs="org.jetbrains.plugins.terminal">
    <commandSpecs path="completionSpecs/all_commands.json"/>
</extensions>
```
```json
{"names":["git"],"description":"The distributed version control system",
 "subcommands":[{"names":["archive"],
   "options":[{"names":["--format"],"args":[{"displayName":"fmt",
     "suggestions":[{"names":["tar"]},{"names":["zip"]}],"default":"undefined"}]}]}]}
```

**Flow:** plugin descriptor declares one EP with one path → loader reads the small index eagerly → typing `git --<TAB>` resolves `loadSpec:"git"` → full spec file parsed on demand → suggestions/templates drive completion.
**Invariant:** the eager plane is ONLY the name→description→loadSpec index; heavy specs are lazy by file. A porter who inlines all specs into one JSON destroys startup latency; one who splits without an index loses discovery.
**Probe:** `unzip -p plugins/terminal/lib/terminal-completion-db-with-extensions.jar completionSpecs/all_commands.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d))"` → `689`; `unzip -l ... | grep -c completionSpecs/` → 1436 total files.
**Coverage caveat:** resource plane inside jars is NOT symbol-indexed; this capsule cites direct jar extraction, not graph nodes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "shell integration command history configureCommandHistory", limit: 5, fields: ["signature", "name", "file"] });
// → plugins/terminal/shell-integrations/bash/bash-integration.bash:111-122 (the runtime side that pairs with this data plane)
```

## Verdict
Adopt the two-level contract: tiny eager index + per-command lazy payload + EP-declared path (works for any CLI/tool catalog). Adapt the JSON field grammar to your host's completion engine. Omit the specific command corpora (they are third-party data snapshots). No direct tests exist for installed builds — deterministic probes above pin behavior.
