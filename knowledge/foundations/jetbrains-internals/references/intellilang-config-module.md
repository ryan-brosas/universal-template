<!-- capsule-v2 -->
# IntelliLang injection config module — how does cross-language injection ship as pure wiring?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-goland`. **Question:** How does a feature that injects one language into another's strings attach itself to an existing language plugin WITHOUT touching that plugin's code?

## Config-only injection descriptor
**Path/Symbol:** `lib/intellij.xml.langInjection.xpath.jar!intellij.xml.langInjection.xpath.xml` (803 bytes, the jar's only member).
**Signature:** `<dependencies><plugin id="XPathView"/></dependencies>` + `<extensions defaultExtensionNs="com.intellij"><applicationService serviceInterface="org.intellij.plugins.intelliLang.inject.config.XPathSupportProxy" serviceImplementation="...XPathSupportProxyImpl"/></extensions>`.
**Data Shape:** cluster census 87 `*langInjection*.xml` across 12 products (goland/rider 9 each; clion/dataspell ~7-8). Each is a standalone micro-descriptor: generated-dependencies region + ONE service/extension registration. The base `intellij.xml.langInjection` module owns injection config storage (`InjectionConfig`); per-host-language modules contribute only a proxy/service binding.

### Decisive source
```xml
<idea-plugin>
  <!-- region Generated dependencies - run `Generate Product Layouts` to regenerate -->
  <dependencies>
    <plugin id="XPathView"/>
    ...
    <module name="intellij.xml.langInjection"/>
  </dependencies>
  <!-- endregion -->
  <extensions defaultExtensionNs="com.intellij">
    <applicationService serviceInterface="org.intellij.plugins.intelliLang.inject.config.XPathSupportProxy"
                        serviceImplementation="org.intellij.plugins.intelliLang.inject.config.XPathSupportProxyImpl"/>
  </extensions>
</idea-plugin>
```

**Flow:** XPathView plugin present → dependency satisfied → micro-descriptor loads → `XPathSupportProxy` applicationService binds XML-injection config persistence to XPath dialect support → IntelliLang's injector consults the proxy when evaluating `<xsl:value-of select="..."/>`-style attribute injections.
**Invariant:** the micro-module NEVER declares its own EPs — it only implements a host-owned interface via service binding, so removing XPathView silently degrades injection instead of breaking boot. Wrong port: making the injected language a hard classpath dep of the injector core.
**Probe:** `unzip -p goland/lib/intellij.xml.langInjection.xpath.jar intellij.xml.langInjection.xpath.xml | grep -c extensionPoint` → `0`; `unzip -l goland/lib/intellij.xml.langInjection.xpath.jar | wc -l` → 2 entries (descriptor + dir).
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "injection language config baseInjection", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: cross-cutting editor features as zero-code config modules that bind host interfaces via applicationService — capability appears only when the provider plugin is installed. Adapt dependency-declaration style to your host's plugin system. Omit the injection pattern-matching internals (base module's domain). This generalizes pass-3's embedded-engine-reuse-radler finding: optional-capability wiring via `<dependencies><plugin id=…/>` + minimal implementation modules.
