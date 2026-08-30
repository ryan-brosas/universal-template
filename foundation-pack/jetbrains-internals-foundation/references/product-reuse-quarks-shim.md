<!-- capsule-v2 -->
# Product-reuse shim plugin — how does a derived product re-use another product's IDE-layer classes without depending on that whole product?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/dataspell-pycharmQuarksIde` ("Parts of PyCharm that are reused in DataSpell IDE"). Codebase Memory `jetbrains-dataspell`. **Question:** What mechanism lets DataSpell register PyCharm-community implementation classes behind platform interfaces, including replacing a PLATFORM service?

## Foreign-impl applicationService re-registration + overrides="true" swap
**Path/Symbol:** `plugins/dataspell-pycharmQuarksIde/lib/dataspell-pycharmQuarksIde.jar:META-INF/plugin.xml` (whole descriptor, ~30 lines; id `com.intellij.dataspell.pycharmQuarksIde`, `implementation-detail="true"`).
**Signature:** `<applicationService serviceInterface="com.jetbrains.python.run.PyCommonOptionsFormFactory" serviceImplementation="com.intellij.pycharm.community.ide.impl.PyIdeCommonOptionsFormFactory"/>` (×2 pairs) and `<applicationService serviceInterface="com.intellij.openapi.module.ModuleTypeManager" serviceImplementation="…PythonModuleTypeManager" overrides="true"/>`.
**Data Shape:** dependencies are just `<plugin id="com.intellij.modules.python"/>` + `<module name="intellij.jupyter.py"/>`; extensions additionally carry one `registryKey key="dataspell.interpreter.widget" defaultValue="true"` feature flag and two `projectConfigurable` entries (content-entries, dependencies) with provider classes.

### Decisive source
```xml
<idea-plugin implementation-detail="true">
  <name>DataSpell PyCharm QuarksIde</name>
  <description><![CDATA[Parts of PyCharm that are reused in DataSpell IDE]]></description>
  <extensions defaultExtensionNs="com.intellij">
    <registryKey key="dataspell.interpreter.widget" defaultValue="true" description="Interpreter widget for lightweight interpreter management" />
    <applicationService serviceInterface="com.jetbrains.python.run.PyCommonOptionsFormFactory"
                        serviceImplementation="com.intellij.pycharm.community.ide.impl.PyIdeCommonOptionsFormFactory" />
    <applicationService serviceInterface="com.intellij.openapi.module.ModuleTypeManager"
                        serviceImplementation="com.intellij.pycharm.community.ide.impl.PythonModuleTypeManager" overrides="true" />
  </extensions>
</idea-plugin>
```

**Flow:** DataSpell wants PyCharm's run-options UI, dependency configurables, and Python module-type behavior → instead of depending on the PyCharm IDE plugin (which would drag its whole product layer), this shim re-registers the specific PyCharm-community impl classes under their SERVICE interfaces → where the interface belongs to the PLATFORM (`ModuleTypeManager`), `overrides="true"` authorizes REPLACING the existing registration rather than colliding with it → the registry key gates the surfaced widget so the swap ships dark-launchable.
**Invariant:** `overrides="true"` is the ONLY sanctioned way for a second descriptor to bind an already-bound service interface — without it the duplicate registration is an error, with it the LAST override wins and ordering between competing overrides is unspecified (never stack two). Distinguish from the ACTION system's `overrides="true"` (`action-override-replacement`): same attribute name, different registry, different semantics — services replace implementations, actions neutralize by id. The shim pattern keeps the reuse surface explicit: every borrowed class appears exactly once, reviewable, in one tiny descriptor.
**Probe:**
```bash
cd /mnt/hdd/utopia/inspo/dataspell/plugins && unzip -p dataspell-pycharmQuarksIde/lib/dataspell-pycharmQuarksIde.jar META-INF/plugin.xml | grep -c 'overrides="true"'        # -> 1 (only the platform-interface swap)
unzip -p dataspell-pycharmQuarksIde/lib/dataspell-pycharmQuarksIde.jar META-INF/plugin.xml | grep -c 'serviceInterface='                                                     # -> 3
```

## Get live surrounding code
Descriptor plane not symbol-indexed; Retrieve = unzip probe above, cross-checked against the platform service vocabulary in the graph:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "ModuleTypeManager python module type", limit: 5 });
```

## Verdict
Adopt: when deriving a product from sibling products, extract the reused IDE-layer registrations into a named implementation-detail shim with explicit serviceInterface→foreignImpl pairs; use `overrides="true"` sparingly and only where you truly replace platform behavior. Adapt which services are swappable in your host. Omit the PyCharm class bodies themselves (proprietary; referenced, never vendored).
