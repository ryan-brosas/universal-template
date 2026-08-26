<!-- capsule-v2 -->
# Plugin registry — first-position-wins dedupe, per-entity config, and CorePlugin immortality

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** What happens when the same plugin appears twice with different options, and how do per-entity plugin options stay isolated from global instances?

## PluginRegistry + descriptor/configurator
**Path/Symbol:** `packages/abstract/src/core/plugins/registry.ts:18-162`, `utilities.ts:18-61` (`configure`/`configurator`/`descriptor`), per-entity auto-registration in `entities/draggable/draggable.ts:70-81` + lookup `pluginConfig` :113-124.
**Signature:** `set values(entries)` — reduce to unique descriptors KEEPING FIRST POSITION but applying LAST options; `register(plugin, options?)` returns the existing instance when already present (options updated in place); `unregister` destroys; `CorePlugin` subclasses are never unregistered by a values-swap (:69-77).
**Data Shape:** entries are `Constructor | {plugin, options}` normalized by `descriptor()`; instances keyed by constructor in an insertion-ordered Map.

### Decisive source
```ts
const descriptors = entries.map(descriptor).reduce((acc, descriptor) => {
  const existing = acc.find(({plugin}) => plugin === descriptor.plugin);
  if (existing) {
    existing.options = descriptor.options;   // last options win
    return acc;                              // first position kept
  }
  return [...acc, descriptor];
}, []);
...
for (const plugin of this.#previousValues) {
  if (!constructors.includes(plugin)) {
    if (plugin.prototype instanceof CorePlugin) continue;   // core plugins survive
    this.unregister(plugin);
  }
}

// Per-entity config is DESCRIPTOR-ONLY — never mutates the shared instance:
const desc = toDescriptor(entry);
if (desc.plugin === plugin) return desc.options;   // Draggable.pluginConfig
```

**Flow:** manager/entity declares plugins → registry dedupes (position = first occurrence, options = rightmost) → removed non-core plugins get destroyed → each constructor instantiated once with merged options. Entities listing plugins AUTO-REGISTER them globally on registration (so Feedback/AutoScroller exist when needed) but their descriptor options remain per-entity queryable via `pluginConfig()` — the global instance stays unconfigured. Auto-registered plugins outlive their source entity if that entity is destroyed mid-drag.
**Invariant:** exactly one instance per constructor; ordering guarantees earlier plugins can resolve later-declared dependencies at construction (pinned :69-92); consumers must read per-entity options through `pluginConfig`, never from `instance.options`.
**Probe:** `packages/abstract/tests/plugin-registry.test.ts:39-341` (dedupe order+options matrix, instance-count assertions, mid-drag survival, pluginConfig isolation incl. global-vs-entity divergence) — executed GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "PluginRegistry", name_pattern: "^PluginRegistry$", limit: 10 });
```

## Verdict
Adopt first-position/last-options dedupe and the two-tier (global instance / entity descriptor) option model; adapt CorePlugin immortality to your extension lifecycle; omit configurator sugar if your API takes descriptors directly.
