<!-- capsule-v2 -->
# Action override replacement — neutralize inherited actions by id

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (pycharm-core.xml); Codebase Memory `jetbrains-pycharm`. **Question:** How does a product disable or replace an action inherited from the platform WITHOUT touching the platform descriptor?

## action overrides
**Path/Symbol:** `lib/intellij.pycharm.community.jar:META-INF/pycharm-core.xml` (`<actions>` block; PyCharm.MarkRootGroup additions).
**Signature:** `<action overrides="true" id="<existing-id>" class="FQN|com.intellij.openapi.actionSystem.EmptyAction"/>` + normal `<group id=...>` extension via `<add-to-group group-id="G" anchor="first|after" relative-to-action="A"/>`.
**Data Shape:** overrides=true = REPLACE the registered class for that id (EmptyAction = permanent no-op); groups/actions attach into existing menus with anchor+relative positioning.

### Decisive source
```xml
<group id="PyCharm.MarkRootGroup">
  <action id="MarkSourceRoot" class="...MarkJavaSourceRootAction"/>
  <action id="MarkExcludeRoot" class="...MarkExcludeRootAction"/>
  <add-to-group group-id="MarkRootGroup"/>
</group>
<action overrides="true" id="ForceStepInto" class="com.intellij.openapi.actionSystem.EmptyAction"/>
```

**Flow:** platform registers an action under an id → product/plugin re-declares the SAME id with overrides="true" → container swaps (or nulls) the implementation while every menu/keymap reference to the id keeps working.
**Invariant:** overriding is BY ID and reference-safe — keymaps bound to the original id automatically hit the replacement. Wrong port: deleting the platform declaration (breaks references) or re-registering under a new id (leaves dead UI).
**Probe:** deterministic: `unzip -p lib/intellij.pycharm.community.jar META-INF/pycharm-core.xml | grep 'overrides'` → ForceStepInto neutralized in PyCharm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "action system update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt id-stable command registry with override-by-redeclaration; adapt EmptyAction equivalent as explicit no-op marker; omit IntelliJ action-update threading. Coverage caveat: direct jar read.
