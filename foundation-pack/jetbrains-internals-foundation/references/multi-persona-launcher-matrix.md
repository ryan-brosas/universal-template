<!-- capsule-v2 -->
# multi-persona-launcher-matrix — how does ONE install boot as backend IDE, thin client, headless linter, and MCP server?

**Source:** JetBrains installed distributions (proprietary), PyCharm Linux `262.9437.214` decisive instance; verified shape in webstorm/clion/goland/rustrover/rubymine/phpstorm/datagrip/dataspell/rider. **Question:** How do multiple process personalities share one binary tree without forking configs?

## launch[] + customCommands persona table
**Path/Symbol:** `<ide>/product-info.json:launch[0]` (main) + `launch[0].customCommands[]`.
**Signature:** `launch[i] = {os, arch, launcherPath, javaExecutablePath, vmOptionsFilePath, startupWmClass, bootClassPathJarNames[], additionalJvmArguments[], mainClass, customCommands[{commands[], vmOptionsFilePath?, bootClassPathJarNames?, additionalJvmArguments?, mainClass, envVarBaseName?, dataDirectoryName?}]}`.
**Data Shape:** PyCharm main launch: `mainClass=com.intellij.idea.Main`, 63 JVM args, full boot classpath (~300 jars). Four customCommands:

### Decisive source
```json
{"commands": ["thinClient", "thinClient-headless", "installFrontendPlugins"],
 "bootClassPathJarNames": ["platform-loader.jar"],
 "additionalJvmArguments": ["-Dintellij.platform.runtime.repository.path=$IDE_HOME/modules/module-descriptors.dat",
   "-Dintellij.platform.root.module=intellij.pycharm.frontend.split",
   "-Dintellij.platform.product.mode=frontend", "-Didea.platform.prefix=JetBrainsClient",
   "-Didea.paths.customizer=...FrontendProcessPathCustomizer"],
 "mainClass": "com.intellij.platform.runtime.loader.IntellijLoader",
 "envVarBaseName": "JETBRAINS_CLIENT", "dataDirectoryName": "PyCharm2026.2"},
{"commands": ["qodana"], "additionalJvmArguments": ["...","-Djava.awt.headless=true",
   "-Didea.platform.prefix=Python","-Dqodana.application=true","-Dqodana.build.number=QDPY-262.9437.214"], "...": "full backend classpath"},
{"commands": ["stdioMcpServer"], "vmOptionsFilePath": "bin/mcp-server.vmoptions",
 "bootClassPathJarNames": ["platform-loader.jar","util-8.jar","util.jar","product-backend.jar","...","+ ../plugins/mcpserver/lib/mcpserver.jar +3 more"],
 "mainClass": "com.intellij.mcpserver.stdio.McpStdioRunnerKt"}
```
A fourth command family (`ijLight`) boots the same frontend split with a restricted `-Didea.load.plugins.id=...` allowlist.

**Flow:** launcher script dispatches subcommand → selects persona entry → overrides/extends JVM args and boot classpath → different `mainClass` (`com.intellij.idea.Main` for full IDE vs `IntellijLoader` for frontend-split personas vs `McpStdioRunnerKt` for MCP) → same `$IDE_HOME`, same module repository file (`modules/module-descriptors.dat`), different `product.mode`/`platform.prefix` system properties select which modules activate.
**Invariant:** ALL personas read the SAME `modules/module-descriptors.dat` runtime repository — personas differ ONLY by bootstrap properties/classpath slices, never by duplicated config trees. The thin-client personas boot from `platform-loader.jar` ALONE (loader pulls everything else via the repository), while backend personas enumerate the full jar list.
**Probe:** `python3 -c "import json;l=json.load(open('pycharm/product-info.json'))['launch'][0];print([c['commands'] for c in l['customCommands']]);print(l['customCommands'][1]['mainClass'])"` → `[['thinClient','thinClient-headless','installFrontendPlugins'],['ijLight'],['qodana'],['stdioMcpServer']]` and `com.intellij.platform.runtime.loader.IntellijLoader`. Cross-IDE check: every full install's `launch[0].customCommands` contains a qodana + stdioMcpServer entry.
**Retrieve:** not a graph seam (JSON manifest): `grep -o '"stdioMcpServer"' <ide>/product-info.json` must hit once per full install.

## Verdict
Adopt the pattern: one distribution, N personas selected by (vmoptions file, boot classpath slice, mainClass, platform-prefix property) — the cleanest shipped example of "monorepo binary, role-at-boot". Adapt persona names/properties to your host. Omit the specific IntelliJ loader classes. Caveat: air/mps ship single-persona launches (no customCommands observed).
