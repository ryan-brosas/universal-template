<!-- capsule-v2 -->
# EP declaration redundancy — product jars re-declare platform extension points

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` (PRO jar `intellij.pycharm.pro.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** Why does a PRODUCT plugin descriptor re-declare extension points the platform already declares — and what must a registry porter conclude from duplicate EP declarations?

## The phenomenon
**Path/Symbol:** `lib/intellij.pycharm.pro.jar:META-INF/PythonPlugin.xml` — 1,404 `<extensionPoint>` declarations, among them verbatim RE-declarations of platform EPs: `search.topHitProvider`, `search.optionContributor`, `search.projectOptionsTopHitProvider`, `statistics.applicationUsagesCollector`, `statistics.projectUsagesCollector`, `statistics.gotItTooltipAllowlist`, `workspaceModel.fileIndexContributor`, `searchEverywhere.tabFactory`, `searchEverywhere.itemsProviderFactory` — each byte-identical in interface/beanClass to its `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` / `intellij.platform.projectModel.impl.jar` original.
**Signature:** `<extensionPoint name="<same-fq-name>" interface="<same-FQN>" dynamic="true"/>` repeated across jars.
**Data Shape:** the PRO jar is simultaneously (a) a merged descriptor carrying ~1.4k EP declarations for modules it hosts and (b) an OVERRIDE-SAFE mirror of EPs its own extensions consume — declaration duplication is tolerated by name; LAST/first-wins resolution is internal, but consumers reference EPs by qualified NAME so both copies serve.

### Decisive source
```xml
<!-- intellij.pycharm.pro.jar:META-INF/PythonPlugin.xml (excerpt around first search.* block) -->
<extensionPoint name="search.topHitProvider" interface="com.intellij.ide.SearchTopHitProvider" dynamic="true" />
<extensionPoint name="search.projectOptionsTopHitProvider"
                interface="com.intellij.ide.ui.OptionsSearchTopHitProvider$ProjectLevelProvider" dynamic="true" />
<extensionPoint name="search.optionContribu... <!-- continues -->
```
Platform twin: `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` carries the identical `search.topHitProvider` line.

**Flow:** classpath loads platform jar → registers EP catalog → loads product merged descriptor → re-registers same-named EPs → resolution by qualified name remains unambiguous because declarations are byte-compatible.
**Invariant:** duplicate EP names are SAFE only while interface/beanClass/dynamic stay IDENTICAL; a porter who "fixes" the duplication by renaming or diverging attributes breaks every consumer resolved by name. Wrong port: assuming one-EP-one-jar uniqueness.
**Probe:** from install root: `unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -c '<extensionPoint\b'` → 1404; `| grep -c 'name="search\.topHitProvider"'` → 1 (and PlatformExtensionPoints.xml → 1: two jars, one name).

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface. Deterministic primitive:
```bash
unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -o 'name="[a-zA-Z.]*topHitProvider"'
```
→ both topHit variants at pin.

## Verdict
Adopt name-keyed EP catalogs that tolerate byte-identical re-declaration (merged-descriptor products need it); adapt scoping rules to your host; omit IntelliJ's classloader-per-plugin rationale beyond the observable contract. Boundary: plugin-mirror-descriptor-class owns module-descriptors.jar root-tag dispatch; this capsule owns EP-CATALOG duplication semantics inside normal plugin jars.
