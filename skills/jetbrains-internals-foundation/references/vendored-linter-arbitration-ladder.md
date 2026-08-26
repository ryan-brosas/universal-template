<!-- capsule-v2 -->
# Vendored external-linter arbitration ladder — how does an external analysis tool integrate WITHOUT fighting the built-in formatter/save stack?

**Source:** JetBrains GoLand installed distribution (proprietary; study/reference use only) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** vendoring a third-party linter into a product — which declaration surfaces must it win, and which must it deliberately lose?

## Third-party plugin, JetBrains-vendored: identity + embedded library module
**Path/Symbol:** `plugins/go-linter/lib/go-linter.jar!META-INF/plugin.xml` — id `com.ypwang.plugin.go-linter` (original author Yupeng Wang credited in description), vendor=JetBrains, root attr `allow-bundled-update="true"`; `<content><module name="intellij.libraries.tuweni.toml" loading="embedded"><![CDATA[<idea-plugin visibility="private" />]]></module></content>`.
**Signature:** `<externalAnnotator language="go" implementationClass="…GoLinterExternalAnnotator"/>` + `<localInspection language="go" … enabledByDefault="false" level="WARNING" unfair="true"/>`.
**Data Shape:** lint pipeline = annotator (on-the-fly) + inspection wrapper (batch/suppression UI); settings = projectSettings×3 + applicationSettings×1 + projectConfigurable groupId="go"; telemetry = counter+project collectors; save arbitration = two ordered replacements against built-in gofmt ids.

### Decisive source
```xml
<idea-plugin package="com.intellij.go.linter" allow-bundled-update="true">
  <content>
    <module name="intellij.libraries.tuweni.toml" loading="embedded"><![CDATA[<idea-plugin visibility="private" />]]></module>
  </content>
  <extensions defaultExtensionNs="com.intellij">
    <formattingService implementation="com.intellij.go.linter.fmt.GoLinterFmtFormattingService" order="before GoFmtFormattingService" />
    <applicationService serviceInterface="com.intellij.codeInsight.actions.onSave.FormatOnSavePresentationService"
                        serviceImplementation="com.intellij.go.linter.fmt.GoLinterFmtOnSavePresentationService"
                        overrides="true" order="before GoFmtOnSavePresentation" />
    <localInspection language="go" enabledByDefault="false" level="WARNING" editorAttributes="INFO_ATTRIBUTES" unfair="true"
                     implementationClass="com.intellij.go.linter.GoLinterInspection" />
  </extensions>
</idea-plugin>
```

**Flow:** golangci-lint runs external → annotator paints on-the-fly results → inspection re-exposes them to suppression/batch UI (disabled by DEFAULT so opting in is explicit; `unfair="true"` exempts it from fair-inspection balancing) → user saves → linter's FormatOnSave presenter wins presentation over gofmt's (overrides+order-before) while its formattingService outranks GoFmtFormattingService for the actual format call → TOML config parsing rides the embedded private tuweni module (no version leakage to consumers).
**Invariant:** a vendored tool may outrank built-ins ONLY at named arbitration points (formattingService order-before + onSave presenter override) while staying opt-in at the inspection layer — winning everywhere is a UX bug. Embedded pure-library modules are EMPTY self-closing descriptors: visibility=private + loading=embedded = shaded dependency, invisible to EP consumers. `allow-bundled-update="true"` marks bundled plugins whose lifecycle can detach from the atomic release pin (`bundled-plugin-exact-pin` exception).
**Probe:** `unzip -p plugins/go-linter/lib/go-linter.jar META-INF/plugin.xml | grep -c 'order="before GoFmt'` → `2`; `unzip -p plugins/go-linter/lib/go-linter.jar META-INF/plugin.xml | grep -c allow-bundled-update` → `1`.

## Get live surrounding code
**Retrieve:** (zero-symbol expectation; coverage check recorded)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "golangci linter external annotator", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/go-linter/lib/go-linter.jar"] });
```

## Verdict
Adopt: vendor-with-attribution identity, empty private library modules for shaded deps, opt-in inspections + named-point arbitration over built-ins. Adapt: config format and tool invocation. Omit: assuming marketplace update semantics — that is host policy around allow-bundled-update.
