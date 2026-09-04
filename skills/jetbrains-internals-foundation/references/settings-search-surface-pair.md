<!-- capsule-v2 -->
# Settings search surface pair — search.topHitProvider and search.optionContributor

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** How do options become findable from "Search Everywhere"/Help→Find Action style typing, and which of the two EPs does a porter need?

## Two settings-search seams
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="search.topHitProvider" interface="com.intellij.ide.SearchTopHitProvider" dynamic="true"/>` and `<extensionPoint name="search.optionContributor" interface="com.intellij.ide.ui.search.SearchableOptionContributor" dynamic="true"/>`.
**Signature:** `<search.topHitProvider implementation="<SearchTopHitProvider FQN>"/>` (py 36) | `<search.optionContributor implementation="<SearchableOptionContributor FQN>"/>` (py 22, ws 24).
**Data Shape:** topHitProvider = runtime provider consulted for TOP hits while typing (returns option rows on demand); optionContributor = supplies a SearchableOptionProcessor that INDEXES every configurable's display name + description into the settings-search corpus up front.

### Decisive source
```xml
<!-- usage: intellij.platform.ide.impl.jar:META-INF/LangExtensions.xml (EditorOptionsTopHitProvider row) -->
<search.topHitProvider implementation="com.intellij.application.options.editor.EditorOptionsTopHitProvider"/>
<!-- PRO RE-DECLARATION: intellij.pycharm.pro.jar:META-INF/PythonPlugin.xml declares BOTH
     search.topHitProvider AND search.projectOptionsTopHitProvider again (see ep-declaration-redundancy) -->
```

**Flow:** user types in search → platform first asks every topHitProvider for immediate matches → deeper Settings-page matches come from the indexed corpus built by walking each optionContributor.
**Invariant:** the two are complementary layers of ONE feature (instant hits vs full-corpus indexing); dropping either silently halves settings discoverability. Wrong port: registering an optionContributor but never feeding its processor (index stays empty), or expecting topHitProviders to appear inside Settings dialog pages (they only serve the popup-level search).
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<search\.topHitProvider\b' | wc -l; done | awk '{s+=$1} END{print s}'` → 36 (py); same for `<search\.optionContributor\b` → 22.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface. Deterministic primitive:
```bash
unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -c 'name="search\.topHitProvider"'
```
→ 1 (PRO jar re-declares the EP; companion evidence for ep-declaration-redundancy).

## Verdict
Adopt the instant-provider + indexed-contributor pair as one feature contract; adapt names; omit IntelliJ's OptionsSearch machinery details. Boundary: precomputed shard index lives in searchable-options-index; this capsule owns the LIVE REGISTRATION SEAMS that feed it.
