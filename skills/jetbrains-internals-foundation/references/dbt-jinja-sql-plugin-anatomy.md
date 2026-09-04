<!-- capsule-v2 -->
# dbt SQL-in-Jinja plugin anatomy — how does one bundled plugin teach a template language to a SQL engine and get Run/Debug for free?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/dbt/lib/dbt.jar` `META-INF/plugin.xml` (5,527 bytes, read whole). Codebase Memory `jetbrains-dataspell` (jar plane; deterministic unzip probes). **Question:** What is the minimal descriptor shape for "SQL files that are really Jinja templates" — composite language wiring, run-config plumbing, and the Python-gated slice?

## Composite-language stack + producer triad + own commandLinePatcher EP consumed by an optional Python module
**Path/Symbol:** `dbt.jar:META-INF/plugin.xml`; content module `intellij.dbt.python` (embedded CDATA); EP `com.intellij.dbt.commandLinePatcher` (interface `com.intellij.dbt.run.DbtCommandLinePatcher`, dynamic).
**Signature:** `<idea-plugin package="com.intellij.dbt" allow-bundled-update="true">`, id `org.jetbrains.dbt`, `idea-version since-build == until-build == 261.26222.84` (atomic-release self-pin).
**Data Shape:** dependencies: `intellij.jinja` module + plugins `com.intellij.database`, modules `intellij.database.dialects.generic`, `intellij.yaml.backend`, `intellij.json.backend`, plugin `com.intellij.diagram`. Python work is quarantined in ONE content module: `<module name="intellij.dbt.python"><dependencies><plugin id="com.intellij.modules.python"/></dependencies>` contributing only `directoryProjectGenerator PyV3DbtGenerator` + `dbt.commandLinePatcher PyDbtCommandLinePatcher`.

### Decisive source
```xml
<!-- SQL-in-Jinja composite stack -->
<lang.substitutor language="SQL" implementationClass="…DbtLanguageSubstitutor" order="first"/>
<outerLanguageRangePatcher language="SQL" implementationClass="…DbtOuterLanguagePatcher"/>
<lang.parserDefinition language="DjangoTemplate"
   implementationClass="com.intellij.jinja.parsing.Jinja2ParserDefinition"/>  <!-- REUSES Jinja's parser under DjangoTemplate -->
<lang.braceMatcher language="DjangoTemplate" implementationClass="…DbtJinjaBraceMatcher"/>
<typedHandler implementation="…DbtJinjaTypedHandler"/>
<lang.elementManipulator forClass="com.intellij.jinja.tags.Jinja2FunctionCall"
   implementationClass="…DbtJinja2FunctionCallManipulator"/>

<!-- producer triad, all order=first; plus own configurationType + line marker -->
<runConfigurationProducer implementation="…producer.DbtRunRunConfigurationProducer" order="first"/>
<runConfigurationProducer implementation="…producer.DbtTestRunConfigurationProducer" order="first"/>
<runConfigurationProducer implementation="…producer.DbtShowRunConfigurationProducer" order="first"/>
<runLineMarkerContributor language="SQL" implementationClass="…DbtRunLineMarkerContributor"/>
<configurationType implementation="…DbtRunConfigurationType"/>

<!-- own EP, filled by the python-gated module -->
<extensionPoint qualifiedName="com.intellij.dbt.commandLinePatcher"
                interface="com.intellij.dbt.run.DbtCommandLinePatcher" dynamic="true"/>
```
Plus the surrounding data-plane claims: `fileType name="YAML" fileNames="dbt_project.yml"` (no new file type — re-key YAML), `JavaScript.JsonSchema.ProviderFactory → DbtYmlSchemaProviderFactory` (schema-aware editing of dbt_project.yml), `Pythonid.templateLanguageCoreTags language="Jinja2" … order="before jinja2"` (dbt tags precede stock Jinja tags), `sql.resolveExtension DbtSqlExtension`, `database.virtualFileDataSourceProvider`, one `localInspection DbtConfigurationInspection`, FUS collectors, `registryKey dbt.models.max.depth.level defaultValue="10"`.

**Flow:** a `.sql` file containing Jinja is substituted by `DbtLanguageSubstitutor order="first"` (SQL host, Jinja injections) → range patching keeps outer/inner ranges consistent → parsing of injected regions delegates to Jinja's OWN parser registered under the `DjangoTemplate` language (no new parser written) → references resolved via two `psi.referenceContributor`s (Jinja2 + DjangoTemplate) and `sql.resolveExtension` → Run intent comes from line markers on SQL; three producers (`order="first"`) synthesize Run/Test/Show configurations before generic producers → before launch, every contributed `commandLinePatcher` mutates the dbt CLI args — the Python module adds its patcher only when Python exists.
**Invariant:** the base plugin is fully functional WITHOUT Python (highlighting, resolution, schema, SQL-side running); Python-only behavior enters exclusively through the optional content module gated on `com.intellij.modules.python`. The extension point boundary between them is a plugin-owned EP (`dbt.commandLinePatcher`), not a platform EP.
**Probe:** deterministic jar probes (executed byte-for-byte this pass):
```bash
unzip -p plugins/dbt/lib/dbt.jar META-INF/plugin.xml          # whole 5.5KB descriptor (captured above)
unzip -l plugins/dbt/lib/dbt.jar | grep META-INF               # plugin.xml + intellij.dbt.python.kotlin_module + intellij.dbt.kotlin_module
```

## Get live surrounding code
**Retrieve:** jar plane not symbol-indexed by design; retrieval = pinned unzip probe above; graph anchor for the shared Jinja host:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "jinja parser django template substitutor", limit: 5 });
```

## Verdict
Adopt: composite-language recipe (substitutor order=first + outerLanguageRangePatcher + reuse an existing template parser under its canonical language name + brace matcher/typed handler/manipulator), producer-triad run stack with order=first preemption, plugin-owned patcher EP as the optional-host join seam. Adapt languages and producers to your pair. Omit the diagram/dataSource contributions unless your target has a database toolwindow plane.
