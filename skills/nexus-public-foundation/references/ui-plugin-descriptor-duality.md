<!-- capsule-v2 -->
# UI plugin descriptor duality — how do plugins declare UI assets so the host aggregates them without hard-coding, across both the ExtJS and React generations?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-rapture/.../UiPluginDescriptor.java` + `nexus-ui-plugin/.../UiPluginDescriptor.java`, 5 descriptor impls); Codebase Memory `nexus-public`. **Question:** When your app hosts UI contributed by optional modules, what contract do contributors implement and how is load order controlled without a registry?

## Two parallel SPIs: legacy ExtJS (pluginId/hasStyle/hasScript/namespace/configClassName) vs modern React (name + explicit script/style lists); order = jakarta @Priority DESC
**Path/Symbol:** `public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/UiPluginDescriptor.java` (`getPluginId` :36, `hasStyle` :38, `hasScript` :40, `@Nullable getNamespace` :46, `@Nullable getConfigClassName` :52; class `@Deprecated` :29 "only if your plugin is including UI content using ExtJs"); `public/common/components/nexus-ui-plugin/src/main/java/org/sonatype/nexus/ui/UiPluginDescriptor.java` (:24 interface; `getName` :26, `getScripts(boolean isDebug)` :31, `getStyles` :36).
**Signature:** `String getPluginId(); boolean hasStyle(); boolean hasScript(); String getNamespace(); String getConfigClassName(); List<String> getScripts(boolean isDebug)` (legacy) / `String getName(); List<String> getScripts(boolean isDebug); List<String> getStyles()` (modern).
**Data Shape:** Descriptors are plain `@Component @Singleton` beans; aggregation happens by constructor-injecting `List<UiPluginDescriptor>` — there is no central registration API. Legacy support class defaults `hasStyle=true`/`hasScript=true` (`UiPluginDescriptorSupport.java` :36/:38) meaning "generate conventional `<pluginId>-{mode}.css|js` paths from my artifactId".

### Decisive source
```java
// nexus-rapture/internal/UiPluginDescriptorImpl.java :33-41 — base shell always first
@Priority(Integer.MAX_VALUE) // always load first
public class UiPluginDescriptorImpl extends UiPluginDescriptorSupport {
    super("nexus-rapture");
    setConfigClassName("NX.app.PluginConfig");

// nexus-coreui-plugin ... :32-40 — each contributor claims its slot in the ladder
@Priority(Integer.MAX_VALUE - 100) // after nexus-rapture
    super("nexus-coreui-plugin");
    setNamespace("NX.coreui");
    setConfigClassName("NX.coreui.app.PluginConfig");

// formats/nexus-repository-maven ... :32-39 — format plugin with no stylesheet
@Priority(Integer.MAX_VALUE - 300) // after proui
    super("nexus-repository-maven");
```

**Flow:** module ships a `@Component` descriptor → Spring collects all of them into the aggregator's injected `List`s → list order follows `@Priority` descending (rapture MAX_VALUE → coreui MAX-100 → pro-ui/onboarding/maven MAX-300) → aggregator emits `<script>`/`<link>` tags in that exact order (see rapture-web-resource-bundle capsule). Modern React descriptors additionally resolve their own bundle URLs at construction via `UiUtil.getPathForFile(...)` (`UiReactPluginDescriptorImpl` :37-53 builds `nexus-rapture-bundle.js/.debug.js/.css` lists once).
**Invariant:** (1) The base shell's descriptor must sort FIRST — every other implementation reserves its slot by subtracting from `Integer.MAX_VALUE`; two modules claiming the same slot have undefined relative order (priority ladder is cooperative, not enforced). (2) The two interfaces are NOT interchangeable despite the identical simple name — the aggregator injects both types as separate lists and never mixes them. (3) `namespace`/`configClassName` are nullable: a descriptor that only contributes static assets omits them.
**Probe:** `nexus-rapture/src/test/java/org/sonatype/nexus/rapture/internal/RaptureWebResourceBundleTest.java` :81-126 — `testGetStyles`/`testGetScripts_prod` pin the aggregated tag order produced by one React + two ExtJS test descriptors; grep anchor: `grep -c '@Priority' public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/UiPluginDescriptorImpl.java` = 1.
**Retrieve:** search_graph project nexus-public query "UiPluginDescriptor getPluginId getNamespace Priority" — resolves `...rapture.internal.UiPluginDescriptorImpl` :33-41, `...coreui.internal.UiPluginDescriptorImpl` :32-40 line-exact.
**Verdict:** Adopt the collect-via-DI + priority-ladder pattern and the explicit asset-list contract for new-style contributors. Adapt the annotation pair (@Priority vs Spring @Order are both present; pick your host's convention). Omit the ExtJS namespace/configClassName machinery unless porting an ExtJS-classic host.
