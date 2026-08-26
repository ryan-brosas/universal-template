<!-- capsule-v2 -->
# Settings theme lazy singleton — defer a host-package dependency out of extension startup

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** How do you move a host-package runtime dependency out of module evaluation so an extension loads instantly, without any command surface running before the deferred value exists?

## Lazy-singleton pair over one dynamic import
**Path/Symbol:** `index.ts:85-97` (`loadedSettingsListTheme` slot + `loadSettingsListTheme` :86-91 + `requireSettingsListTheme` :92-97); consumers `index.ts:836` (preload), `index.ts:862` (`SettingsList` ctor arg), `index.ts:389` (`settingsSubmenu`). Introduced upstream in 921b9a8 "perf(extension): load the settings-list theme on first picker use".
**Signature:** `const loadSettingsListTheme = async (): Promise<SettingsListTheme>` and `const requireSettingsListTheme = (): SettingsListTheme`.
**Data Shape:** one module-level slot `let loadedSettingsListTheme: SettingsListTheme | undefined`; the loader memoizes via `??=` around a single `await import("@earendil-works/pi-coding-agent")`; the getter is synchronous and throws `Error("Settings list theme accessed before /openai-settings preload")` when the slot is still empty. `SettingsListTheme` itself stays a STATIC type-only import — types cost nothing at runtime.

### Decisive source
```ts
// pi-core's getSettingsListTheme pulls the host module graph into this
// extension's loader (~0.5s of startup). The settings picker is a command-time
// surface, so the theme loads when it first opens.
let loadedSettingsListTheme: SettingsListTheme | undefined;
const loadSettingsListTheme = async (): Promise<SettingsListTheme> => {
  loadedSettingsListTheme ??= (
    await import("@earendil-works/pi-coding-agent")
  ).getSettingsListTheme();
  return loadedSettingsListTheme;
};
const requireSettingsListTheme = (): SettingsListTheme => {
  if (!loadedSettingsListTheme) {
    throw new Error("Settings list theme accessed before /openai-settings preload");
  }
  return loadedSettingsListTheme;
};
```

**Flow:** module evaluation only *defines* the pair (zero host-module loading) → user invokes `/openai-settings` → `showSettingsPicker` checks `hasTerminalUI`, then `await loadSettingsListTheme()` runs BEFORE the pets fetch and `ctx.ui.custom(...)` mount → inside the mounted component, `new SettingsList(..., requireSettingsListTheme(), ...)` and `settingsSubmenu`'s `const theme = requireSettingsListTheme()` read the now-filled slot synchronously → subsequent picker opens skip the import entirely (`??=` latch).
**Invariant:** (1) module evaluation performs no host-module loading — the ~0.5s graph pull happens once, on first picker open, never at startup; (2) exactly ONE dynamic import exists and it is memoized, so the expensive factory runs at most once per process; (3) every synchronous consumer sits behind the single awaited preload on the ONLY entry path, and the guard fails LOUDLY naming the missed preload instead of silently substituting a default theme; (4) static-vs-dynamic split follows cost: type-only imports stay static, value imports that drag the host module graph become dynamic.
**Probe:** No upstream unit test drives this path (picker tests mock the TUI layer) — coverage caveat recorded. Deterministic source probes (run from repo root): `grep -c 'loadedSettingsListTheme ??=' index.ts` → 1 (single memoized import); `grep -c 'await import("@earendil-works/pi-coding-agent")' index.ts` → 1 (the ONLY runtime host import left in `index.ts`; all other host references in `src/*` are type-only); `grep -c 'requireSettingsListTheme()' index.ts` → 2 (the two consumer call sites :389/:862; the definition itself does not match this pattern), `grep -c 'getSettingsListTheme' index.ts` → 2 (comment :83 + dynamic call :89, NO static import remains).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "loadSettingsListTheme requireSettingsListTheme", limit: 10, fields: ["signature", "name", "file"] });
```
(Verified live at pin `1188f985`: total:2, exact spans `index.ts` 86-91 and 92-97.)

## Verdict
Adopt the lazy-singleton pair: empty-slot declaration, `??=`-memoized async loader around one dynamic import, a synchronous require-guard that throws naming the missed preload, and exactly one `await load…()` before the first consumer on the entry path. Adapt which package counts as "host", what the heavy factory is, the error wording, and where the preload sits in your command handler. Omit the pi-specific `getSettingsListTheme()` semantics and the `/openai-settings` command wiring unless targeting pi itself.
