<!-- capsule-v2 -->
# Provider service facade — how do you expose one provider-owned account/preference service shared by arbitrary optional front doors without changing host defaults?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** where should singleton credentials and live policy live when Web routes, terminal commands, and client UI may each mount or not mount independently?

## OpenAICodexService delegation plane
**Path/Symbol:** `src/service.ts:34-82 OpenAICodexService`, `src/service.ts:25-28 OpenAICodexServiceOptions`, `src/service.ts:17-22 Context interface augmentation`.
**Signature:** `new OpenAICodexService(options: OpenAICodexServiceOptions)` with `attachSettings(ctx)`, `login(interaction)`, `logout()`, `authStatus()`, `usage()`, `imagePreferences()`, `updateImagePreferences(patch)`, `responsePreferences()`, `updateResponsePreferences(patch)`.
**Data Shape:** the class exposes exactly two owned singletons — `readonly credentials = new OpenAICodexCredentialStore()` and `readonly policy: ImageToolPolicy` — plus pure delegating methods; `OpenAICodexServiceOptions extends ImageToolPreferences, ResponseApiPreferences` and adds `models?: string[]` + `modelCatalog`. Preference getters return detached snapshots; updaters return persisted snapshots.

### Decisive source
```ts
export class OpenAICodexService {
  readonly credentials = new OpenAICodexCredentialStore()
  readonly policy: ImageToolPolicy

  constructor(options: OpenAICodexServiceOptions) {
    this.policy = new ImageToolPolicy(options, options.modelCatalog)
  }

  attachSettings(ctx: Context): void {
    this.policy.attach(ctx)
  }

  /** Read current subscription limits without issuing a model request. */
  usage(): Promise<OpenAICodexUsage> {
    return readOpenAICodexRateLimits(this.credentials)
  }

  imagePreferences(): ImageToolPreferences { return this.policy.snapshot() }
  updateImagePreferences(patch): Promise<ImageToolPreferences> { return this.policy.update(patch) }
  responsePreferences(): ResponseApiPreferences { return this.policy.responseApiSnapshot() }
  updateResponsePreferences(patch) { return this.policy.updateResponseApi(patch) }
}
// declare module '@deepseek-ai/cordis' { interface Context { openAICodex: OpenAICodexService } }
```

**Flow:** bundle configuration → constructor builds one policy over the configured catalog → front door mounts call `attachSettings(ctx)` to bind the durable settings document when the active profile provides one → the service is provided into the host context as `ctx.openAICodex` → any front door (terminal command tree `status/login/logout/usage/config/set`, Web auth/settings routes, client UI) resolves the same instance and delegates.
**Invariant:** exactly one credential store and one policy exist regardless of how many front doors are mounted ("Credentials and live policy stay singletons even when several front doors are mounted"); all validation/migration/persistence rules live inside `ImageToolPolicy`/`store.ts` — the facade adds no logic of its own; `usage()` reads rate limits from stored credentials and never issues a model request; nothing here mutates host defaults.
**Probe:** `tests/tui.spec.ts` pins the facade's consumed contract with a structural fake (`authStatus/usage/login/logout/imagePreferences/updateImagePreferences/responsePreferences/updateResponsePreferences`), asserts the optional-TUI command tree registers children `status/login/logout/usage/config/set`, and that `set native-compaction on` calls `updateResponsePreferences({ useNativeCompaction: true })`. Caveat recorded honestly: the class itself has no dedicated unit spec; its correctness is delegated to the tested `tool-policy`/`store`/`auth`/`usage` planes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.service\\.OpenAICodexService\\.(usage|constructor|attachSettings)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 3, has_more false. Graph trace note: inbound callers of `OpenAICodexService.usage` reported 0 by the graph while `tests/tui.spec.ts:100` exercises it through the terminal adapter — source wins over graph under-reporting.

## Verdict
Adopt the two-singleton facade with pure delegation and a typed context slot so optional front doors can come and go. Adapt the DI mechanism (context augmentation vs container), the option shape, and which operations are exposed. Omit embedding OAuth logic, quota parsing, or persistence rules into the facade — keep them in their own capsules. Coverage: `src/service.ts` is `no_recorded_issue` + `metadata_match`; no dedicated direct-test file exists for the class itself (structural fake in `tests/tui.spec.ts` is the boundary evidence).
