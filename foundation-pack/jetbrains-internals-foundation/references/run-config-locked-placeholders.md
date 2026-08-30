<!-- capsule-v2 -->
# Locked run-configuration placeholders — why a product ships types meant to be overwritten

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml` inside `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** How does the community layer reserve framework Run-dialog slots (Django/Flask/dbt/FastAPI) so pro plugins can fill them WITHOUT forking the registration site?

## Placeholder configurationType quartet
**Path/Symbol:** `plugins/python-ce/lib/modules/intellij.python.community.impl.jar:intellij.python.community.impl.xml:294-298`.
**Signature:** `<configurationType implementation="com.jetbrains.python.run.<X>LockedRunConfigurationType" order="first"/>` — four consecutive declarations (DjangoServer, FlaskServer, DbtRun, FastAPI), each with `order="first"`; preceded by the comment `<!-- Locked configurations should go first to be overwritten by real ones-->`; followed by `<facetIgnorer implementation="com.jetbrains.python.run.DjangoFacetIgnorer"/>`.
**Data Shape:** placeholder = real `ConfigurationType` EP contribution with a `*Locked*` class name and forced-first ordering; the overwriting plugin later contributes its own configurationType for the same feature (e.g. PRO module declares `FastApiRunConfigurationType`, `FlaskRunServerConfigurationType`, `CeleryRunConfigurationType`).

### Decisive source
```xml
<!-- Locked configurations should go first to be overwritten by real ones-->
<configurationType implementation="com.jetbrains.python.run.DjangoServerLockedRunConfigurationType" order="first"/>
<configurationType implementation="com.jetbrains.python.run.FlaskServerLockedRunConfigurationType" order="first"/>
<configurationType implementation="com.jetbrains.python.run.DbtRunLockedConfigurationType" order="first"/>
<configurationType implementation="com.jetbrains.python.run.FastAPILockedRunConfigurationType" order="first"/>
```
Overwriters in the PRO module (`plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:75,88,151`): `FastApiRunConfigurationType`, `FlaskRunServerConfigurationType`, `CeleryRunConfigurationType`.

**Flow:** community base ships FIRST a minimal placeholder type per framework → when the richer plugin is present its real configurationType also registers and supersedes the slot; if the richer plugin is absent the placeholder still gives users a working entry point instead of an empty Run dialog.
**Invariant:** the reservation must ship in the BASE layer with forced-first ordering, and naming marks intent (`Locked` = do not treat as final). Wrong port: shipping the placeholder in the optional plugin (slot disappears when plugin absent) or omitting `order="first"` (placeholder may sort after the real type). Naming trap: the suffix pattern is inconsistent — `DbtRunLockedConfigurationType` puts `Locked` mid-name, so greps keyed on `*Locked*Type` undercount (3 of 4); grep `Locked.*ConfigurationType` or read the block.
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | sed -n '294,298p'` → 4 placeholder lines + ownership comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "python test runner suite execution", limit: 10, fields: ["signature", "name", "file"] });
```
(placeholder types have no helper-side code plane; retrieval demonstrates the adjacent runner helpers, e.g. `pydev_runfiles.py` PydevTestRunner.)

## Verdict
Adopt the base-layer-placeholder + ordered-overwrite pattern for any capability registry where an optional premium/extended provider may or may not be present; adapt the marker (`Locked`) to your host's naming; omit IntelliJ's ConfigurationType runtime. Coverage caveat: manifest read from jar.
