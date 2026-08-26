<!-- capsule-v2 -->
# Adapter assembly policy — how should an adapter lift legacy replay state on read, split model advertisement from resolution, and tune retries for proxy-blip-prone traffic?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** which adapter-assembly behaviors keep persisted sessions portable across provider-library upgrades and a model directory honest, without forking the generic pi-ai adapter? (Stream purpose-marking is `responses-transport-choice.md`; Fast Mode decoration is `fast-mode-registry.md`.)

## Read-time migration + advertise/resolve split
**Path/Symbol:** `src/adapter.ts:32-45 migrateLegacyOpenAICodexReplayState`, `src/adapter.ts:47-60 migrateReplayHistory`, `src/adapter.ts:140-146 OpenAICodexAdapter.listModels`, `src/adapter.ts:68-72 OPENAI_CODEX_RETRY_POLICY`, `src/adapter.ts:23 OPENAI_CODEX_STREAM_IDLE_TIMEOUT_MS`, profile wiring in `createOpenAICodexAdapter` (`src/adapter.ts:166-190`).
**Signature:** `migrateLegacyOpenAICodexReplayState(value: unknown): unknown`; `override async listModels(provider: string)`; `OPENAI_CODEX_RETRY_POLICY = resolveRetryPolicy({ mode: 'normal', maxRetries: 5, backoff: { initialDelayMs: 1_000, maxDelayMs: 30_000, jitterRatio: 0.2 } }, 'dsh-openai-codex retryPolicy')`.
**Data Shape:** legacy replay envelope `{ kind: 'pi-ai', version: 1, blocks: unknown[], …response }` lifts to `{ response: { …response, kind: 'pi-ai', version: 2 }, blocks }`; visibility input is `visibleModelIds?: () => readonly string[]` (undefined = full catalog; explicit array = advertisement filter).

### Decisive source
```ts
export function migrateLegacyOpenAICodexReplayState(value: unknown): unknown {
  const legacy = record(value)
  if (legacy?.['kind'] !== 'pi-ai' || legacy['version'] !== 1 || !Array.isArray(legacy['blocks'])) return value
  const { blocks, kind: _kind, version: _version, ...response } = legacy
  return { response: { ...response, kind: 'pi-ai', version: 2 }, blocks }
}

override async listModels(provider: string) {
  const models = await super.listModels(provider)
  const visibleModelIds = this.visibleModelIds?.()
  if (visibleModelIds === undefined) return models
  const visible = new Set(visibleModelIds)
  return models.filter(model => visible.has(model.id))
}
// stream() wraps: for await (const chunk of super.stream(migrateReplayHistory(options))) yield chunk
```
Retry rationale (source comment): "Codex traffic rides on chatgpt.com, which is frequently reached through a local proxy tunnel that blips for tens of seconds at a time. The dsh default stops after 2 retries and caps scheduled delays at 10 seconds, so this provider retries longer and backs off further to ride out such a blip."

**Flow:** harness resume → `stream()` maps every model message's `replayState` through the migrator (unchanged payloads keep the SAME options object — no reallocation when nothing migrated) → generic pi-ai adapter consumes the current envelope. Model listing → `super.listModels` → optional filter to the configured visible id set (deduped via Set). Profile assembly resolves the retry policy once at module load and attaches it to the single provider route together with the 300 s idle ceiling.
**Invariant:** migration is read-time and identity-preserving for current-version payloads (only exact `kind:'pi-ai' version:1` with an array `blocks` is lifted); advertisement and resolution are independent — filtering `listModels` to zero or a subset never blocks `resolveModel` on a hidden id (`'gpt-5.4'` still resolves while unadvertised), so config controls visibility, not routability; the extended retry policy stays bounded (5 attempts, 1 s→30 s, jitter 0.2) rather than unbounded.
**Probe:** `tests/adapter.spec.ts` (4 cases: omitted vs explicitly empty `models` config distinguished; registered route returns exactly `OPENAI_CODEX_RETRY_POLICY` matching `{ maxRetries: 5, initialDelayMs: 1000, maxDelayMs: 30000, jitterRatio: 0.2, retryableCodes ⊇ RATE_LIMIT/SERVER/TIMEOUT/TRANSPORT }`; duplicated visible ids advertise `['gpt-5.6-luna','gpt-5.6-terra']` while hidden `'gpt-5.4'` remains resolvable; unconfigured config advertises the full catalog incl. `gpt-5.4/gpt-5.6-luna/gpt-5.6-sol/gpt-5.6-terra`). The migration function has NO dedicated spec — a deterministic Node strip-types probe against the actual source was executed instead (legacy v1 lifted to versioned envelope; current-shape payload returned by identity).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.adapter\\.(migrateLegacyOpenAICodexReplayState|migrateReplayHistory)$', limit: 10 });
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.adapter\\.OpenAICodexAdapter\\.(listModels|stream)$', limit: 10 });
```
Executed live against project `dsh-codex`: totals 2 and 2, both has_more false.

## Verdict
Adopt read-time identity-preserving state lifting, the advertise-vs-resolve split driven by a detached id set, and a named bounded retry policy tuned to known network path behavior with its rationale written next to the constants. Adapt envelope shapes, retry budgets, and where visibility configuration lives. Omit write-back migrations on load, conflating hidden models with unroutable ones, or unbounded retry loops. Coverage: `src/adapter.ts` and `tests/adapter.spec.ts` are `no_recorded_issue` + `metadata_match`; migration probe executed deterministically as recorded above.
