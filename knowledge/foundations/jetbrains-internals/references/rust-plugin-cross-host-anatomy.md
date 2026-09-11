<!-- capsule-v2 -->
# rust-plugin-cross-host-anatomy — how does one IDE's whole engine ship as a plugin that other IDEs install?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instance (intellij-rust). **Question:** How does a product (RustRover) package its entire engine as a single `com.jetbrains.rust` plugin whose feature slices activate per host IDE?

## com.jetbrains.rust descriptor: product-as-plugin with host-gated content modules
**Path/Symbol:** `rustrover/plugins/intellij-rust/lib/intellij-rust.jar:META-INF/plugin.xml` → `<id>com.jetbrains.rust</id>`, `<version>262.9437.161</version>`, `<idea-version since-build="262.9437.161" until-build="262.9437.161"/>`; `<content namespace="jetbrains">` declares exactly 26 modules `intellij.rustrover.*`.
**Signature:** `content module name = intellij.rustrover.<slice>`; slice set: common(embedded), core, frontend, frontend.split, idea, debugger, debugger.runners, profiler, valgrind, clion, nativeDebug{,.idea,.rustrover}, copyright, duplicates, coverage, grazie, js, ml-completion, terminal, rustrover-only, sql, mcp, monolith(internal), webLibraries, backend.split.
**Data Shape:** gating is declared as ORDINARY `<dependencies>` inside each module's CDATA payload — a module activates iff all named deps resolve: plugin ids (`com.intellij.clion`, `com.intellij.nativeDebug`, `com.intellij.copyright`, `com.intellij.diagram`, `com.intellij.completion.ml.ranking`), capability tokens (`com.intellij.modules.rustrover`), or platform modules (`intellij.cidr.*`, `intellij.clion.execution`, `intellij.java.backend`, `intellij.rustrover.core`). Boot-slice modules add `required-if-available="intellij.platform.backend|frontend|frontend.split"` on the module node itself.

### Decisive source
```xml
<id>com.jetbrains.rust</id>
<description><![CDATA[This plugin adds the power of RustRover ... to IntelliJ IDEA, CLion, and PyCharm.
<b>Starting with version 2026.2</b>, the Rust plugin requires the Native Debugging Support
(plugin id: <code>com.intellij.nativeDebug</code>) to be installed.]]></description>
<dependencies><plugin id="org.toml.lang" /><plugin id="com.intellij.modules.ultimate" /></dependencies>
<incompatible-with>org.rust.lang</incompatible-with>
<content namespace="jetbrains">
  <module name="intellij.rustrover.common" loading="embedded"><![CDATA[<idea-plugin visibility="public">…]]>
  <module name="intellij.rustrover.clion"><![CDATA[<idea-plugin>
    <dependencies><plugin id="com.intellij.clion" /><plugin id="com.intellij.nativeDebug" />
      <module name="intellij.cidr.runner" />…</dependencies>]]></module>
  <module name="intellij.rustrover.nativeDebug.idea"><![CDATA[<idea-plugin><dependencies>
    <module name="intellij.rustrover.debugger" /><plugin id="com.intellij.nativeDebug" />
    <module name="intellij.java.backend" /></dependencies>]]></module>
```

**Flow:** host boots → resolves `com.jetbrains.rust` top-level deps (toml + ultimate + lang + regexp) → walks content modules; each module's CDATA dependencies are evaluated against the host's plugin/module repository → in RustRover: `.rustrover-only` and `.nativeDebug.rustrover` activate (capability token present), `.clion` stays dormant (no com.intellij.clion plugin — CIDR ships only as modules), `.nativeDebug.idea` dormant (no java.backend need met... it requires intellij.java.backend which IS present in RR? no: it also targets IDEA hosts where Java support exists); in CLion/IDEA the mirror-image subset activates.
**Invariant:** ONE jar must stay host-neutral — every host-specific behavior lives behind a dependency-gated content module; the top-level descriptor may only depend on capabilities every target host provides. The legacy community plugin id (`org.rust.lang`) must be blocked via `<incompatible-with>` or two Rust engines could coexist.

**Probe:** `python3 -c "import zipfile,re;x=zipfile.ZipFile('rustrover/plugins/intellij-rust/lib/intellij-rust.jar').read('META-INF/plugin.xml').decode();print(len(re.findall(r'<module name=\"intellij.rustrover[^\"]*\"( loading=\"[^\"]+\")?( required-if-available=\"[^\"]+\")?>',x)));print('required-if-available' in x, 'incompatible-with' in x)"` → `26` then `True True`. Declarations end in `>`; the 46 dependency references self-close with ` />` (raw substring count `<module name=\"intellij.rustrover` = 72 = 26 + 46).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rustrover", file_pattern: "plugins/intellij-rust/**", query: "rust plugin modules", limit: 10 });
```
(jar XML is not symbol-indexed — graph confirms the plugin dir surface; decisive text read from the jar.)

## Verdict
Adopt: one-engine-many-hosts distribution = top-level neutral deps + per-host CDATA-gated content modules + hard required companion plugins stated in description AND enforced by module deps. Adapt: your capability-token vocabulary (`<lang>-capable`, `<product>` tokens). Omit: JetBrains' specific cidr/clion module names. Caveat: verified in the RustRover 2026.2.1 install only; sibling-host activation states inferred from dependency semantics, not booted in other IDEs.
