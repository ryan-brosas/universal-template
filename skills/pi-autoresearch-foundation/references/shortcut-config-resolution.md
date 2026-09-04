<!-- capsule-v2 -->
# Shortcut config resolution — how do two extensions claim the same keys without a war?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the override grammar, and what happens to registrations when a shortcut is disabled?

## resolveAutoresearchShortcuts — profile-local JSON, tri-state values, null disables
**Path/Symbol:** `extensions/pi-autoresearch/src/shortcuts/index.ts:14–52` (resolution), :91–94 (`shortcutFromConfig`), :111–129 (`dashboardHintVariants`); consumers index.ts :980–1001.
**Signature:** `resolveAutoresearchShortcuts(configPath = <agentDir>/extensions/pi-autoresearch.json): AutoresearchShortcuts`; defaults `'ctrl+shift+a'` toggle / `'ctrl+shift+x'` fullscreen.
**Data Shape:** file `{ "shortcuts": { "toggleDashboard": "<keyid>"|null, "fullscreenDashboard": "<keyid>"|null } }`; result `{toggleDashboard: KeyId|null, fullscreenDashboard: KeyId|null}`.

### Decisive source
```ts
function shortcutFromConfig(configured: unknown, fallback: KeyId): KeyId | null {
  if (configured === null) return null;                    // explicit disable wins over default
  return typeof configured === 'string' ? (configured as KeyId) : fallback;  // garbage ⇒ default
}
// index.ts:980 — disabled shortcuts are never REGISTERED at all:
if (shortcuts.toggleDashboard) {
  pi.registerShortcut(shortcuts.toggleDashboard, { ... });
}
```

**Flow:** init → read config (missing file OR unparseable OR invalid shape ⇒ warn-once + full defaults; `shortcuts` key absent ⇒ {} then per-key fallbacks) → resolve each binding through the tri-state ladder → register only non-null bindings. Widget/dashboard HINT TEXT derives from the same resolved object (`dashboardHintVariants`) so the UI never advertises a binding that isn't registered.
**Invariant:** three-valued logic is the contract: `undefined` ⇒ default, valid string ⇒ override, explicit `null` ⇒ DISABLED (not default!) — that distinction is what lets a user free ctrl+shift+x for another extension. Hint variants and actual registrations read ONE resolved struct, so display and behavior cannot diverge. Invalid configs degrade loudly (console.warn) but never crash the extension.
**Probe:** direct test `__tests__/unit/shortcuts.test.ts` (191 lines) pins the resolution matrix incl. null-disable and invalid-config fallbacks; anchors `grep -n "configured === null" extensions/pi-autoresearch/src/shortcuts/index.ts` → :92; `grep -n 'if (shortcuts.toggleDashboard)' extensions/pi-autoresearch/index.ts` → :980.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "resolveAutoresearchShortcuts dashboardHintVariants registerShortcut", limit: 10 });
```

## Verdict
Adopt the tri-state override grammar and hint-from-resolution pattern verbatim; adapt the config location to your host's profile dir; omit nothing. Fully direct-tested.
