<!-- capsule-v2 -->
# code-provenance-plugin-anatomy — what does a shipped AI-telemetry plugin look like, and which IDEs carry it?

**Source:** JetBrains installed distributions (proprietary), PyCharm `plugins/code-provenance/` decisive instance (only install in the cluster that ships it). **Question:** How does JetBrains instrument "was this code typed, pasted, or AI-generated" as a bundled plugin, and what is its module decomposition?

## code-provenance.jar + 7 split modules
**Path/Symbol:** `pycharm/plugins/code-provenance/lib/code-provenance.jar` (22 entries; META-INF/plugin.xml only) + `lib/modules/intellij.code.provenance.{core, core.mcp, core.llm, core.fus, core.git, core.claude, ui, dev}.jar`.
**Signature:** plugin.xml: `<id>com.intellij.code.provenance</id>`, `<idea-version since-build="262.9437.214" until-build="262.9437.214"/>` (exact-pin — every bundled plugin re-declares its exact build, no range), v2 `<content namespace="jetbrains">` with CDATA-embedded module descriptors.
**Data Shape:** description declares scope: "collects fine-grained information about how code changes are made — whether a piece of code was typed, pasted, completed, the result of a refactoring, or added by an AI agent or AI-backed action… used for building code statistics, developer behavior analysis, or improving the context provided to LLMs." Disabling "may change behavior of features that use this data."

### Decisive source
```xml
<name>Code Provenance by Qodana</name>
<description><![CDATA[The Code Provenance plugin provides analytics to AI features in the IDE and JetBrains Cloud Platform.
    It comes pre-installed in supported JetBrains IDEs, and does not require any configuration. …]]></description>
<dependencies>
  <module name="intellij.platform.lvcs.impl" />
</dependencies>
<content namespace="jetbrains">
  <module name="intellij.code.provenance.dev"><![CDATA[<idea-plugin>
  <dependencies><plugin id="Git4Idea" />
    <module name="intellij.code.provenance.core" />
    <module name="intellij.code.provenance.core.git" />
    <module name="intellij.vcs.git.backend" /> …</dependencies>
  <actions resource-bundle="messages.ProvenanceDevBundle">
    <group id="CodeProvenance.Dev.Actions" internal="true" po…
```

**Flow:** editor/LVCS change events → provenance core classifies change origin (typed/pasted/completed/refactoring/AI-agent) → per-sink modules consume it (`core.llm` feeds LLM context builders, `core.fus` feature-usage stats, `core.git` attributes VCS changes, `core.mcp`/`core.claude` expose agent-side surfaces, `ui` renders markers, `dev` exposes internal action group) → dependency root is `lvcs.impl` (local VCS), the minimal seam for observing edits.
**Invariant:** classification rides the LVCS dependency alone; each consumer is a SEPARATE module so disabling one sink never breaks capture. The `internal="true"` dev actions keep instrumentation tooling out of user menus.
**Probe:** `ls pycharm/plugins/code-provenance/lib/modules/` → 8 jars ending `{core,core.mcp,core.llm,core.fus,core.git,core.claude,ui,dev}.jar`; presence check across cluster: `for i in webstorm clion goland rider datagrip dataspell air mps phpstorm; do test -d $i/plugins/code-provenance && echo "$i YES" || echo "$i no"; done` → only pycharm YES among these installs.
**Retrieve:** graph covers the code plane only where indexed: search_graph project jetbrains-pycharm query "provenance" returns the plugin's classes if under an indexed helpers dir; otherwise use `unzip -p pycharm/plugins/code-provenance/lib/code-provenance.jar META-INF/plugin.xml`.

## Verdict
Adopt: provenance tracking as a pluggable pipeline — single capture core, per-consumer modules, exact-pin idea-version for bundled coherence; model any "where did this artifact come from" telemetry on it. Adapt sinks to host. Omit proprietary classifier internals (.class bytecode). Caveat: distribution varies by product/install channel — absence elsewhere is an install fact, not a platform rule.
