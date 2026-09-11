<!-- capsule-v2 -->
# Client slot injection entry — how does a plugin's browser half mount several UI surfaces into host slots while keeping every dependency injectable and every session-scoped resource reclaimed?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** where does browser plugin initialization live when one bundle must contribute a settings page, a tool-result view, and two composer controls without hard-wiring fetch, translation, or model-directory services?

## One entry, four slots, effect-owned resources
**Path/Symbol:** `src/client/index.tsx:31-33 name`+`inject` exports, `src/client/index.tsx:36-101 apply`, `src/client/index.tsx:23-28 LocaleNamespaceMap augmentation`, `src/client/index.tsx:42-56 imageUrls` cache, `src/client/locales.ts:77 OpenAICodexSettingsKey`.
**Signature:** `export const name = 'dsh-codex-client'`; `export const inject = ['slots', 'locale', 'sessions']`; `export function apply(ctx: ClientContext): void`.
**Data Shape:** the module-level `inject` array declares host services the loader must supply before `apply` runs; every surface receives its dependencies through an `*Injected` interface (`OpenAICodexSettingsInjected { t }`, `OpenAICodexFastModeToggleInjected`/`OpenAICodexQuotaIndicatorInjected { directory: SnapshotStore<ModelDirectoryState> }`, `ImagegenToolViewProps += loadImage, t`) instead of importing them.

### Decisive source
```ts
export const name = 'dsh-codex-client'
export const inject = ['slots', 'locale', 'sessions']

export function apply(ctx: ClientContext): void {
  const namespace = 'settings.openai-codex'
  ctx.effect(() => ctx.locale.register(namespace, { zh, en }), 'dsh-openai-codex: settings copy')
  const t = ctx.locale.bind(namespace) as OpenAICodexSettingsInjected['t']
  const imageUrls = new Map<string, Promise<string>>()
  // loadImage(sessionId, attachment): key `${sessionId}:${attachmentId}`;
  //   caches the PROMISE, creates object URLs, tracks them in createdUrls
  ctx.effect(() => () => {
    for (const url of createdUrls) URL.revokeObjectURL(url)
    createdUrls.clear()
    imageUrls.clear()
  }, 'dsh-openai-codex: release image URLs')
  ctx.slots.inject('settings.section', () => ctx.slots.register({
    name: 'settings.section', id: 'openai-codex', order: 15,
    label: () => t('nav'), inject: (): OpenAICodexSettingsInjected => ({ t }),
  }, OpenAICodexSettings))
  ctx.inject(['slots', 'modelDirectories'], scope => {
    scope.slots.inject('conversation.input.right', () => scope.slots.register({
      name: 'conversation.input.right', id: 'openai-codex-fast-mode', order: 10,
      inject: (sessionId) => ({ directory: scope.modelDirectories.directoryFor(sessionId).store }),
    }, OpenAICodexFastModeToggle))
    // ... second registration id 'openai-codex-quota' order 20 -> OpenAICodexQuotaIndicator
  })
}
```

**Flow:** host loads the built bundle → resolves declared services `['slots','locale','sessions']` → calls `apply(ctx)` once → locale namespace registered under an effect (unregistered on teardown) and bound translate handed to every surface → settings page registered at order 15, imagegen tool view keyed `'imagegen'` with a per-session `loadImage` closure, composer surfaces registered inside a scoped re-inject so `modelDirectories.directoryFor(sessionId).store` is resolved per session at render time → `loadImage` deduplicates by `${sessionId}:${attachmentId}` key, caching the promise (not the URL), deleting the entry on failure so retries re-fetch.
**Invariant:** resources live exactly as long as the plugin: locale copy and every created object URL are released through paired `ctx.effect` cleanups; the cache never stores bare strings (so concurrent callers share one in-flight load); components never import host services — they receive them via `*Injected`, which is what makes all three component spec suites able to mount them with plain fakes; adding an English copy key without a Chinese counterpart fails to compile because `zh` is typed `{ [Key in OpenAICodexSettingsKey]: string }`.
**Probe:** no dedicated spec exists for `index.tsx` itself (grep over `tests/` finds no reference to the entry). Boundary evidence recorded honestly: each component spec constructs exactly the `*Injected` shapes `apply` produces (`directory` store fake, `t` over `en`), pinning the wiring contract by consumption; resource-reclaim behavior is enforced structurally by the effect-pairing shown above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.(apply|inject|name)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 3, has_more false (`apply` Function 36-101, `inject` Function 96-98, `name` Variable 31). Graph caveat: the node labeled `inject` is the slot-registration closure at line 96, not the module-level service array at line 33 — confirmed by direct read; `apply` shows zero graph edges because the host bundle loader invokes it without an import edge (source wins).

## Verdict
Adopt the single-entry `name`/`inject`/`apply` triad with slot registrations whose `inject` factories resolve session-scoped state lazily, plus effect-owned registration/reclamation pairs. Adapt the slot names, the service list, and the DI container to your host. Omit eager service resolution inside `apply` — anything per-session belongs behind a factory closure. Coverage: `src/client/index.tsx` and `src/client/locales.ts` are `no_recorded_issue` + `metadata_match`; the entry has no dedicated direct-test file (recorded caveat).
