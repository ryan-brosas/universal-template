<!-- capsule-v2 -->
# native-buildsystem-import-spine — how do alternative build systems plug into a C++ IDE's project model?

**Source:** JetBrains CLion installed build `2026.2.1@262.9437.136` (`plugins/clion-compdb/lib/clion-compdb.jar:META-INF/plugin.xml` 88L, `plugins/clion-meson/lib/clion-meson.jar:...` 120L, `plugins/clion-makefile/lib/clion-makefile.jar:...` 113L — direct jar reads); Codebase Memory `jetbrains-clion`. **Question:** What is the minimal descriptor stack that makes an external build system a first-class citizen (open, import, configure, build, status) beside the native default?

## The externalSystemManager spine + ordered open ladder
**Path/Symbol:** each build-system plugin contributes the SAME `com.intellij` stack: `externalSystemManager` + `externalProjectDataService` (model import) + `projectOpenProcessor` (entry, ORDERED) + `projectConfigurable groupId="build" groupWeight="1080"` + `projectTaskRunner`; plus `cidr.project` namespace: `workspaceProvider`, `widget.widgetStatusProvider`, `notifications.editorNotificationWarningProvider`, `popup.projectFixesProvider`. Makefile additionally DECLARES its own EPs: `clion.makefile.buildSystemDetector` / `clion.makefile.projectPreConfigurator` (`dynamic="true"`).
**Signature:** `<projectOpenProcessor id="X" order="first, after|before <Sibling>ProjectOpenProcessor"/>`.
**Data Shape:** open-processor precedence ladder encodes import priority: Meson = `order="first, before MakefileProjectOpenProcessor, after CMakeProjectOpenProcessor"`; CompDB = `order="first, after MakefileProjectOpenProcessor"` ⇒ effective chain CMake > Meson > Makefile > CompilationDatabase. All three pin since==until==buildNumber (bundled-plugin-exact-pin).

### Decisive source
```xml
<!-- clion-compdb.jar META-INF/plugin.xml (unzip -p, direct read) -->
<externalSystemManager implementation="com.jetbrains.cidr.cpp.compdb.CompDBManager" />
<externalProjectDataService implementation="...compdb.project.CompDBStateDataService" />
<projectOpenProcessor id="CompDBProjectOpenProcessor"
    implementation="...compdb.wizard.CompDBProjectOpenProcessor"
    order="first, after MakefileProjectOpenProcessor" />
<projectTaskRunner ... id="CompDBProjectTaskRunner" order="after CMakeProjectTaskRunner" />
<extensions defaultExtensionNs="cidr.project">
  <workspaceProvider implementation="...compdb.CompDBWorkspaceProvider" />
<!-- clion-meson.jar: -->
<projectOpenProcessor id="MesonProjectOpenProcessor" ...
    order="first, before MakefileProjectOpenProcessor, after CMakeProjectOpenProcessor" />
```

**Flow:** user opens a project dir → projectOpenProcessors are consulted in order-ladder sequence until one claims it → the claimed system's Manager/DataServices import the model into the CIDR workspace model → workspaceProvider persists it → status/fix providers surface sync problems → TaskRunner executes builds ordered after the CMake anchor.
**Invariant:** ONE spine, N guests — a new build system needs no platform changes, only the guest EP set; cross-guest ordering is expressed by NAME-STRING anchors on other guests' processors (same anchor currency as extension-ordering-attributes); toolchain changes reach every guest via one shared listener topic (`CPPToolchainsListener`); heavy fragments ride v2 content modules (`intellij.clion.meson.core` loading="required", visibility="internal"; compdb splits its JSON-schema provider into `intellij.clion.compdb.schema` depending on intellij.json).
**Probe:** executed byte-exact pre-write: `unzip -p <jar> META-INF/plugin.xml | grep -E 'extensionPoint|extensions defaultExtensionNs'` per jar (makefile ⇒ own dynamic EPs; compdb/meson ⇒ com.intellij+cidr.project stacks; line counts 88/120/113); open-processor order strings quoted verbatim above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-clion", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/clion-compdb' OR f.file_path STARTS WITH 'plugins/clion-meson' OR f.file_path STARTS WITH 'plugins/clion-makefile' RETURN count(f) AS bs_files", max_rows: 5 });
```
(graph indexes the loose modules/ trees of these plugins; descriptor plane read directly from jars — established cluster caveat.)

## Verdict
Adopt the spine+guest pattern for any host with one first-class build integration and N optional ones — declare the full guest stack per plugin and keep inter-guest priority on named anchors; adapt service/class names; omit CIDR model internals. Cross-references: extension-ordering-attributes owns the order grammar; optional-depends-capability-fragment owns schema-fragment gating.
