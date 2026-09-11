<!-- capsule-v2 -->
# Settings service tiers — projectSettings vs applicationSettings vs Configurable vs advancedSetting

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml` inside `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`; PRO module `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:80-83,170-172`); Codebase Memory `jetbrains-pycharm`. **Question:** Which of the four settings-registration tags applies when — and what breaks if you pick the wrong tier?

## Tier census (one module)
**Path/Symbol:** community: 7× `<projectSettings>` (e.g. :171-172 PRO mirror), 7× `<applicationSettings>`, 4× `<projectConfigurable>`, 4× `<advancedSetting id= default= groupKey=>` (:327-330); PRO: `<projectConfigurable groupId="language" instance=... bundle="messages.PythonProBundle" key="flask.configurable.name" nonDefaultProject="true"/>` (:80-83).
**Signature:** `<projectSettings service="<FQN>"/>` | `<applicationSettings service="<FQN>"/>` | `<projectConfigurable [groupId] instance= id= bundle= key= [nonDefaultProject="true"]/>` | `<advancedSetting id="<string-id>" default="<value>" groupKey="<bundle-key>"/>`.
**Data Shape:** service tags PERSIST state (project-scoped vs IDE-global); Configurable renders a UI page into the tree; advancedSetting injects a single row into the platform's "Advanced Settings" page with a string id + typed default + i18n group.

### Decisive source
```xml
<applicationSettings service="com.intellij.python.pro.duplocator.PyDuplocatorSettings"/>   <!-- IDE-global -->
<projectSettings    service="com.intellij.python.pro.coverage.PyCoverageOptionsProvider"/> <!-- per-project -->
<projectConfigurable groupId="language" instance="...FlaskConfigurable"
                     id="com.intellij.python.pro.flask.configuration.FlaskConfigurable"
                     bundle="messages.PythonProBundle"
                     key="flask.configurable.name" nonDefaultProject="true"/>              <!-- UI page -->
<advancedSetting id="python.pytest.swapdiff" default="false"
                 groupKey="group.advanced.settings.python"/>                               <!-- one row -->
```
(community block :327-330 ships four advancedSettings incl. a numeric default: `python.code.vision.usages.limit` default="500".)

**Flow:** storage layer = services (pick scope by asking "would this setting survive opening a different project?") → presentation layer = configurables referencing stored services → long-tail toggles bypass custom pages entirely via advancedSetting rows.
**Invariant:** the four tiers are ORTHOGONAL axes (scope × presence-of-UI × granularity). Wrong port: registering an application-scoped service as projectSettings (state leaks across projects) or giving advancedSetting a Configurable class instead of a plain provider.
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c '<projectSettings '` → 7; `| grep -c '<applicationSettings '` → 7; `| grep -c '<advancedSetting '` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "user type renderers settings parse", limit: 10, fields: ["signature", "name", "file"] });
```
(settings classes are compiled; helper-side debugger-settings parsing IS indexed, e.g. `_pydevd_bundle/pydevd_user_type_renderers.py:84-130`.)

## Verdict
Adopt the scope-first storage/UI split with a low-ceremony row-level escape hatch; adapt tag names; omit IntelliJ's SettingsRepository sync machinery. Coverage caveat: manifest read from jar. Boundary: tree-shape mechanics live in settings-configurable-tree; this capsule owns the TIER CHOICE.
