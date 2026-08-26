<!-- capsule-v2 -->
# Icon library + expui migration map — how does a UI ship thousands of icons with a theme-rollover layer?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How are icons organized (semantic dirs, dark variants) and how do JSON mapping files migrate an old icon vocabulary to a new one without touching call sites?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.platform.ide.jar` → `expui/**` (1,740 svgs), `PlatformIconMappings.json`; sibling semantic dirs `actions/`(377) `general/`(210) `nodes/`(161) `debugger/`(153) `ide/`(121) `providers/`(107) `toolwindows/`(94) `fileTypes/`(47) `process/big/step_N.svg` — 3,660 svgs total in this one jar.
**Signature:** `<bundledKeymap>`-style data file: `{ "expui": { "actions": { "addFile.svg": "actions/addFile.svg", "checked.svg": ["actions/checked.svg","actions/setDefault.svg"] } } }`.
**Data Shape:** every icon exists in pairs `<name>.svg` + `<name>_dark.svg`. New-vocabulary tree (`expui/`) is flat-semantic; old call sites reference legacy paths; the mapping JSON translates expui-path → legacy-path, with ARRAY values = "several old icons collapse to this new one". Per-domain mapping twins ship beside their domains: ExternalSystemIconMappings.json, VcsIconMappings.json, ProfilerIconMappings.json, SpellcheckerIconMappings.json, CollaborationToolsIconMappings.json, DvcsIconMappings.json, VcsLogIconMappings.json.

### Decisive source
```json
{ "expui": { "actions": {
    "addFile.svg": "actions/addFile.svg",
    "checked.svg": ["actions/checked.svg", "actions/setDefault.svg"],
    "deploy.svg":  "nodes/deploy.svg" } } }
```

**Flow:** renderer asked for `expui/actions/deploy.svg` under a non-expui theme → mapping resolves to `nodes/deploy.svg` → `_dark` suffix rule applies at load. Call sites never change during the migration.
**Invariant:** the `_dark` suffix is a NAMING CONTRACT, not config; array-valued mappings mean many-to-one coalescing must be allowed by any reimplementation.
**Probe:** `unzip -l lib/intellij.platform.ide.jar | grep -c 'expui/'` → ~1,742 entries; `unzip -p lib/intellij.platform.ide.jar PlatformIconMappings.json | head -3`.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "icon lookup path dark theme", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: paired light/dark naming convention, semantic directory taxonomy as API, JSON indirection layer for icon-set migrations with many-to-one support, per-subsystem mapping-file split. Adapt to your host's asset pipeline. Omit the artwork.
