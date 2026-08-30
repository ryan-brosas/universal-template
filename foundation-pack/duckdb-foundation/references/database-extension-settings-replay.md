<!-- capsule-v2 -->
# Extension settings replay — how do unknown config options become live settings after autoload?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the copy-then-replay protocol for unrecognized options, and when does it fail loudly?

## Snapshot map → per-option autoload → SetExtensionVariable in ONE transaction → leftover = error
**Path/Symbol:** `src/main/database.cpp:DatabaseInstance::LoadExtensionSettings` (:250-291); `ThrowExtensionSetUnrecognizedOptions` (:239-248).
**Signature:** `void LoadExtensionSettings()`; guarded by `AutoloadKnownExtensionsSetting`; each option resolved via `ExtensionHelper::FindExtensionInEntries(name, EXTENSION_SETTINGS)`.
**Data Shape:** `config.options.unrecognized_options` is an `identifier_map_t<Value>`; applied through `PhysicalSet::SetExtensionVariable(context, extension_option, SetScope::GLOBAL, value)`.

### Decisive source
```cpp
auto unrecognized_options_copy = config.options.unrecognized_options;  // protect vs mutation
...
Connection con(*this);
con.BeginTransaction();
for (auto &option : unrecognized_options_copy) {
    auto extension_name = FindExtensionInEntries(name, EXTENSION_SETTINGS);
    if (extension_name.empty()) continue;
    if (!TryAutoLoadExtension(*this, extension_name))
        throw InvalidInputException("To set the %s setting, the %s extension needs to be loaded. But it could not be autoloaded.", ...);
    if (!config.TryGetExtensionOption(name, extension_option))
        throw InternalException("Extension %s did not provide the '%s' config setting", ...);
    PhysicalSet::SetExtensionVariable(context, extension_option, SetScope::GLOBAL, value);
}
con.Commit();
if (!config.options.unrecognized_options.empty()) ThrowExtensionSetUnrecognizedOptions(...);
```

**Flow:** snapshot the unrecognized map (the DB may mutate it during autoload) → for each option that some extension owns: autoload it, verify it registered the option, apply globally inside one transaction → anything still unrecognized after the pass throws with the full comma-joined list.
**Invariant:** the loop iterates the COPY while success is measured against the LIVE map; an option claimed by an autoloaded extension must exist post-load or it's an InternalException (engine bug), not a user error.
**Probe:** `grep -c 'con.BeginTransaction()' src/main/database.cpp` → `2`; `grep -n 'PhysicalSet::SetExtensionVariable' src/main/database.cpp` → :283.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "LoadExtensionSettings TryAutoLoadExtension SetExtensionVariable unrecognized_options", limit: 10 });
```

## Verdict
Adopt deferred-setting replay with all-or-nothing transactional application and loud leftovers; adapt your registry lookup; omit the C-API/linked-extension bookkeeping around it.
