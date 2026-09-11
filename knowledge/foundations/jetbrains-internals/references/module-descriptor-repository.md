<!-- capsule-v2 -->
# module-descriptor-repository — how does the runtime know which modules exist and what each may see, without classpath scanning?

**Source:** JetBrains installed distributions (proprietary), PyCharm `modules/` plane decisive instance; same shape in all full installs. **Question:** Where is the authoritative module graph (names, visibility, dependencies, jar paths) that both backend and frontend personas load from?

## modules/module-descriptors.{dat,jar}
**Path/Symbol:** `<ide>/modules/module-descriptors.jar` (human-readable mirror) + `module-descriptors.dat` (runtime binary). Manifest: `Specification-Title: IntelliJ Runtime Module Repository`, `Implementation-Version: 0.1.3`, plus `Bootstrap-Module-Name` / `Bootstrap-Class-Path`.
**Signature:** per-module XML: `<module name="..." namespace="..." visibility="internal|public|private"> <dependencies><module name="..." namespace="..."/></dependencies> <resources><resource-root path="../lib/<name>.jar"/></resources> </module>`.
**Data Shape (PyCharm 262.9437.214):** 1,720 entries = 1,719 xml + MANIFEST; **1,366 v2 module descriptors + 353 `*_$legacy_jps_module.xml`** shims for pre-v2 JPS modules. Visibility distribution: internal=420, public=301, private=528, none=117. Namespaces: jetbrains=1233, `$legacy_jps_module`=110, implicit plugin namespaces (`ru.adelf.idea.dotenv_$implicit`, `com.intellij.database_$implicit`, …) as one-offs.

### Decisive source
```xml
<!-- fleet.andel.xml -->
<module name="fleet.andel" namespace="jetbrains" visibility="internal">
  <dependencies>
    <module name="kotlin-stdlib" namespace="$legacy_jps_library"/>
    <module name="fleet.util.core"/>
    <module name="kotlinx-serialization-json" namespace="$legacy_jps_library"/>
  </dependencies>
  <resources>
    <resource-root path="../lib/fleet.andel.jar"/>
  </resources>
</module>

<!-- plugins/intellij.pycharm.pro.xml — header is the porting trap -->
<!-- The IDE doesn't use this file; it takes data from module-descriptors.dat instead -->
<plugin id="com.intellij">
  <plugin-descriptor-module name="intellij.pycharm.pro" namespace="$legacy_jps_module"/>
  <module name="intellij.platform.core.nio.fs" namespace="$legacy_jps_module" loading="embedded"/>
```

**Flow:** build system emits descriptors → runtime boots with `-Dintellij.platform.runtime.repository.path=$IDE_HOME/modules/module-descriptors.dat` (see multi-persona-launcher-matrix) → loader resolves module→jar via `<resource-root>` (paths relative to the descriptor's dir, hence `../lib/`) → dependency edges gate classloader visibility; plugin-level descriptor files inside the jar re-declare the SAME wiring but are documentation-only.
**Invariant:** the `.dat` binary is the single source of truth at runtime; the `.jar`'s XML files are a readable MIRROR — never parse the XML mirror and assume runtime behavior. `visibility="private"` (528 modules — the largest bucket) hides a module from every other namespace; only `public` (301) is importable across plugins.
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/modules/module-descriptors.jar');n=[x for x in z.namelist() if x.endswith('.xml')];print(len(n),sum('_$legacy_jps_module' in x for x in n))"` → `1719 353`. Visibility census: grep `visibility="` across all v2 descriptors → internal/public/private ≈ 420/301/528.
**Retrieve:** not symbol-indexed (XML in jar): `python3 -c "import zipfile;z=zipfile.ZipFile('<ide>/modules/module-descriptors.jar');print([x for x in z.namelist() if 'pycharm.pro' in x])"`.

## Verdict
Adopt: ship ONE serialized module repository + readable mirror; declare visibility and explicit resource-roots per module instead of classpath scans — this is the substrate that makes multi-persona boot and embedded-vs-optional loading possible. Adapt descriptor format to your host. Omit `.dat` binary format details. Caveat: legacy-jps shims show a migration edge (old modules wrapped, not rewritten) — keep shim names stable when porting incrementally.
