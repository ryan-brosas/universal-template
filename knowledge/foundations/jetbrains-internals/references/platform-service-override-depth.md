<!-- capsule-v2 -->
# Platform service override depth — how far can interface-keyed service overrides go beyond branding, and which override mechanism applies at each granularity?

**Source:** JetBrains GoLand installed distribution (proprietary; study/reference use only) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** `product-customization-plugin-plane` owns the persona/branding override idiom; how DEEP does the same mechanism reach when a product must replace CORE IDE services (recent projects, module types), and which of the three override mechanisms applies where?

## Core-service replacements inside the product's ide module
**Path/Symbol:** `plugins/goland-customization-plugin/lib/goland-customization-plugin.jar!META-INF/plugin.xml` → embedded module `intellij.go.ide` (51 files).
**Signature:** `<applicationService serviceInterface="com.intellij.ide.RecentProjectsManager" serviceImplementation="com.goide.ide.welcomeScreen.GoWelcomeScreenRecentProjectsManager" overrides="true" />`; same form for `ModuleTypeManager → GoModuleTypeManager`.
**Data Shape:** four service-level overrides total (the two CORE services above + ExternalProductResourceUrls + WhatsNewInVisionContentProvider — the latter two are the persona depth already owned by `product-customization-plugin-plane`); plus welcomeScreenProjectProvider order="first"; directoryProjectGenerator trio ending GoEmptyProjectGenerator order="last"; registryKey `go.attach.content.root` whose description self-labels it "a fallback option, it will be removed"; `platform.rpc.backend.remoteApiProvider`.

### Decisive source
```xml
<!-- intellij.go.ide CDATA (goland-customization-plugin.jar!META-INF/plugin.xml) -->
<extensions defaultExtensionNs="com.intellij">
  <applicationService serviceInterface="com.intellij.openapi.module.ModuleTypeManager"
                      serviceImplementation="com.goide.ide.GoModuleTypeManager" overrides="true" />
  <applicationService serviceInterface="com.intellij.ide.RecentProjectsManager"
                      serviceImplementation="com.goide.ide.welcomeScreen.GoWelcomeScreenRecentProjectsManager" overrides="true" />
  <welcomeScreenProjectProvider implementation="com.goide.ide.welcomeScreen.GoWelcomeScreenProjectProvider" order="first" />
</extensions>
<actions resource-bundle="messages.GoBundle">
  <group id="NonModalWelcomeScreen.LeftTabActions.New" overrides="true">
    <reference ref="GoIdeNewProjectAction" /><reference ref="GoIdeNewEmptyProjectAction" /><separator />
  </group>
</actions>
```

**Flow:** platform registers default implementations → product assembly loads the customization plugin → `overrides="true"` swaps the instance behind the STABLE interface → every consumer injecting `RecentProjectsManager`/`ModuleTypeManager` transparently gets product behavior (welcome-screen-owned recents, Go module types) → action-GROUP ids are replaced by a second mechanism (group overrides="true") → contributor-level stacking stays order-anchored (`console-customizer-override-stack`).
**Invariant:** ONE attribute, THREE granularities — service-instance replacement (`overrides="true"` on applicationService), registry-content replacement (`overrides="true"` on an action group id), contributor ordering (`order=`). Depth scaling: RustRover's plane swaps PERSONA SPIs (resources/what's-new); GoLand's additionally swaps CORE workspace/module services — the ceiling is "any interface the platform exposes as a service", so porting teams must treat overridable-SPI surface as API contract, not implementation detail. Registry keys carry self-describing removal promises in descriptions.
**Probe:** `unzip -p plugins/goland-customization-plugin/lib/goland-customization-plugin.jar META-INF/plugin.xml | grep -c 'serviceInterface="com.intellij\(\.ide\.RecentProjectsManager\|\.openapi\.module\.ModuleTypeManager\)"'` → `2`; `… | grep -c '<group id="NonModalWelcomeScreen.LeftTabActions.New" overrides="true">'` → `1`.

## Get live surrounding code
**Retrieve:** (zero-symbol expectation; descriptor plane graph-dark; coverage check recorded)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "RecentProjectsManager ModuleTypeManager override", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/goland-customization-plugin/lib/modules/intellij.go.ide.jar"] });
```

## Verdict
Adopt: scale service overrides from persona SPIs up to core workspace services behind stable interfaces; pick mechanism by granularity (instance / registry content / contributor order); self-document removable hacks in registry descriptions. Adapt: which services your platform designates overridable. Omit: IntelliJ service-container runtime semantics.
