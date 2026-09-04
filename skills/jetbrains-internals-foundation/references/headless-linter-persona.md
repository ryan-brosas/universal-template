<!-- capsule-v2 -->
# Headless linter persona — how does a desktop IDE become a CI command?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does one install binary serve both the IDE and a headless static-analysis run without a second distribution?

## Connected graph-selected seam
**Path/Symbol:** `<install>/product-info.json:launch[0].customCommands[]` entry `{"commands":["qodana"],...}`; companion `bin/inspect.sh` (9 lines) and `bin/format.sh` (6 lines).
**Signature:** customCommand = `{commands:[name...], bootClassPathJarNames:[...], additionalJvmArguments:[...]}` (+ optional `vmOptionsFilePath`).
**Data Shape:** qodana entry carries 264 bootClassPathJarNames, 84 additionalJvmArguments including the identity set `-Dqodana.application=true`, `-Didea.qodana.thirdpartyplugins.accept=true`, `-Dqodana.product.name=Qodana for Python|JS|...`, `-Dqodana.build.number=QDPY-262.9437.214|QDJS-262.9437.145|...`, `-Dqodana.eap=false`, plus the SAME `-Didea.platform.prefix=Python` as the GUI launch.

### Decisive source
```
$ python3 -c "import json;d=json.load(open('product-info.json'));\
print([c['commands'] for c in d['launch'][0]['customCommands']])"
[['thinClient', 'thinClient-headless', 'installFrontendPlugins'], ['ijLight'], ['qodana'], ['stdioMcpServer']]
```
Cluster census of `customCommands` containing `qodana`: pycharm, webstorm, rider, goland, rustrover, clion, rubymine, phpstorm, phpstorm-light = YES; dataspell, datagrip, mps, air, dotmemory, dottrace = NO.
And `bin/inspect.sh` in full:
```sh
#!/bin/sh
export DEFAULT_PROJECT_PATH="$(pwd)"
IDE_BIN_HOME="${0%/*}"
exec "$IDE_BIN_HOME/pycharm.sh" inspect "$@"
```

**Flow:** every persona (GUI/thin-client/ijLight/qodana/stdioMcpServer) is a named command over ONE module repository; the command selects a classpath subset + JVM flags + platform-prefix property; inspect.sh/format.sh are 6–9 line wrappers that exec the main launcher with a subcommand name.
**Invariant:** no separate linter build exists to keep in sync — the CI tool IS the IDE boot with different flags (`-Dqodana.application=true`) and an accept-flag gate for third-party plugins; version identity is inherited (`QDPY-<buildNumber>` embeds the host build).
**Probe:** from `<install>` root:
`python3 -c "import json;d=json.load(open('product-info.json'));print(sum(1 for c in d['launch'][0]['customCommands'] if c['commands']==['qodana']))"` prints `1` (NOTE: a collapsed grep `"commands": \["qodana"\]` is BY-CONSTRUCTION zero on these pretty-printed files — the array spans lines; do not 'repair' to it);
`grep -c '"commands": \[' product-info.json` prints `4` (all personas);
`test -f bin/inspect.sh && test -f bin/format.sh && echo CLI-OK` prints `CLI-OK` on all mainstream products except mps/air/dotmemory/dottrace (no bin tools there).
**Coverage caveat:** manifest plane; search_code resolves only the product-info.json text (`pattern:"qodana"` → 2 hits), jar internals unindexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "applicationStarter command line inspect", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: one-binary multi-persona via declared custom commands with per-command classpath slices — extends multi-persona-launcher-matrix with the LINTER persona and the wrapper-script contract. Adapt: your host's launcher flag surface. Omit: Qodana cloud protocol.
