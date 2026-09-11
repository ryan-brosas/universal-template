<!-- capsule-v2 -->
# Search-everywhere contributor vs tab/provider split — old monolithic and new two-sided architectures coexist

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** Which search-surface registration should a porter copy — the single-contributor EP or the tab+provider pair — and how do they relate?

## Two generations, one popup
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/LangExtensionPoints.xml` — `<extensionPoint name="searchEverywhereContributor" interface="com.intellij.ide.actions.searcheverywhere.SearchEverywhereContributorFactory" dynamic="true"/>`; NEW split: `intellij.platform.searchEverywhere.frontend.jar:META-INF/*.xml` — `<extensionPoint name="searchEverywhere.tabFactory" interface="com.intellij.platform.searchEverywhere.frontend.SeTabFactory" dynamic="true"/>`; `intellij.platform.searchEverywhere.jar` — `<extensionPoint name="searchEverywhere.itemsProviderFactory" interface="com.intellij.platform.searchEverywhere.SeItemsProviderFactory" dynamic="true"/>`.
**Signature:** `<searchEverywhereContributor implementation="<ContributorFactory FQN>"/>` | `<searchEverywhere.tabFactory implementation="<SeTabFactory FQN>"/>` | `<searchEverywhere.itemsProviderFactory implementation="<SeItemsProviderFactory FQN>"/>`.
**Data Shape:** legacy = ONE class owns matching + results rendering per category (Files/Classes/Actions...); new = FRONTEND tabs (presentation) decoupled from BACKEND item providers (matching), wired by the platform (py: 20 contributors, 12 tab factories, 20 provider factories — counts overlap because both stacks ship).

### Decisive source
```xml
<!-- legacy: intellij.platform.ide.impl.jar:META-INF/LangExtensions.xml:1392 -->
<searchEverywhereContributor implementation="com.intellij.ide.actions.searcheverywhere.FileSearchEverywhereContributorFactory"/>
<!-- new backend side: intellij.platform.searchEverywhere.backend.jar:...xml -->
<searchEverywhere.itemsProviderFactory implementation="com.intellij.platform.searchEverywhere.backend.providers.files.SeFilesProviderFactory"/>
<!-- new frontend side: ...frontend.tabs.all.SeAllTabFactory etc. -->
```

**Flow:** popup opens → active TAB chosen (new architecture: SeTabFactory list; legacy: contributor's own tab integration) → providers/contributors produce items for the query → merged, ranked, rendered.
**Invariant:** the same logical category exists in BOTH stacks during migration — "Files" is a legacy contributor AND a Se tab + provider; a porter extending one stack must not assume the other is absent. Wrong port: registering a new-stack provider without any tab that displays its kind.
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<searchEverywhereContributor ' | wc -l; done | awk '{s+=$1} END{print s}'` → 20 (py); `<searchEverywhere\.tabFactory\b` → 12; `<searchEverywhere\.itemsProviderFactory\b` → 20.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface for these EP tokens. Deterministic primitive:
```bash
for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -H --label="$j" 'SeFilesProviderFactory'; done | head -2
```
→ backend jar AND intellij.pycharm.pro.jar both carry the files provider row at pin.

## Verdict
Adopt the frontend/backend split as the target shape with legacy single-class registration as the compatibility tier; adapt naming; omit IntelliJ's popup UI internals. Coverage caveat: top-level-lib census. Boundary: settings-side search lives in searchable-options-index/topHit capsule; this capsule owns GLOBAL GO-ANYWHERE search surfaces.
