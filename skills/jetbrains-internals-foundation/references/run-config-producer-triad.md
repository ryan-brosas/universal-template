<!-- capsule-v2 -->
# Producer→type→runner triad — the three-part run-configuration registration contract

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml` in `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`; PRO module `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml`); Codebase Memory `jetbrains-pycharm`. **Question:** What is the minimal COMPLETE registration set that turns "user right-clicks a file" into an executable configuration — and which of the three parts may be omitted?

## Triad census across both Python modules
**Path/Symbol:** community: `intellij.python.community.impl.xml:292,304,321-326,331-338,810`; PRO: `intellij.python.xml:75,88-89,151-154`.
**Signature:** `<configurationType implementation="<...ConfigurationType>"/>` + `<runConfigurationProducer implementation="<...Producer>"/>` + `<programRunner implementation="<...Runner>" order=.../>` (+ optional `<runLineMarkerContributor language="Python" .../>` for gutter affordance).
**Data Shape:** type = named/template slot (the dialog entry); producer = context-inferrer that MINTS a configuration from a file/facet (many per type); runner = executor chosen at Run time (few per install); line-marker contributor = UI hook surfacing the producer's inference as a gutter icon.

### Decisive source
```xml
<configurationType implementation="com.jetbrains.python.run.PythonConfigurationType"/>          <!-- :292 -->
...
<runConfigurationProducer implementation="com.jetbrains.python.run.PythonRunConfigurationProducer"/>  <!-- :304 -->
...
<runLineMarkerContributor language="Python"
                          implementationClass="com.jetbrains.python.codeInsight.PyRunLineMarkerContributor"/> <!-- :338 -->
```
PRO-side producers pair with framework types: `FlaskRunServerConfigurationProducer` (:89), `CeleryRunAppConfigurationProducer` + `CeleryRunTaskConfigurationProducer` (:152-153), `PyTestsConfigurationProducer`/`PythonDocTestConfigurationProducer`/`PyToxConfigurationProducer` (:324-326).

**Flow:** producer inspects editor context → mints a typed configuration under its configurationType's id space → user triggers execution → platform picks a programRunner by ordering (see run-config-type-runner-ordering) → runner executes. The line marker is pure UI sugar over the producer.
**Invariant:** TYPE is mandatory; RUNNER is mandatory at the platform level but usually inherited from defaults; PRODUCER and MARKER are optional conveniences. Wrong port: registering only a producer without its type (minted configs have nowhere to live), or assuming one-producer-per-type (Python ships three test-family producers over one `PythonTestConfigurationType`).
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c 'runConfigurationProducer implementation'` → 4; same command on `plugins/python/lib/modules/intellij.python.jar intellij.python.xml` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pydev_runfiles PydevTestRunner", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mint-from-context producer pattern with a mandatory owning type; adapt producer granularity to your host's context sources; omit IntelliJ's ExecutionEnvironment plumbing. Coverage caveat: manifest read from jar.
