<!-- capsule-v2 -->
# TUI command-tree completion — how does a plugin register executable commands plus optional bilingual completion trees so neither depends on the other?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** a provider wants `/codex …` to work in any host while a rich TUI (if present) gets typed-ahead subcommand completion with localized descriptions — how do you wire that without hard dependency?

## UI-neutral registration + canonical-path completion responder
**Path/Symbol:** `src/tui.ts:274-278 apply`, `:280-332 registerCodexCommand`, `:334-346 registerTuiCommandTree`, `:83-89 codexSubcommands`, `:58-60 translatedNode`, tables :48-81 (HELP, CODEX_ACTIONS, CODEX_SETTINGS, BOOLEAN_VALUES).
**Signature:** `apply(ctx)` injects into `['commands']` and `['tuiCommandTrees']` independently; `tuiCommandTrees.register(provider {root, descriptions?, children(canonicalPath)}) → () => void`; `codexSubcommands(path: readonly string[]): readonly TuiSubcommandNode[]`.
**Data Shape:** `TuiSubcommandNode = { name, aliases?, description, descriptions?: {en?,zh?}, tag? }` — `translatedNode(name, en, zh)` always fills both locales so dictionary parity is structural.

### Decisive source
```ts
function codexSubcommands(path: readonly string[]): readonly TuiSubcommandNode[] {
  if (path.length === 1 && path[0] === 'codex') return CODEX_ACTIONS
  if (path.length === 2 && path[0] === 'codex' && path[1] === 'set') return CODEX_SETTINGS
  if (path.length === 3 && path[0] === 'codex' && path[1] === 'set'
    && CODEX_SETTINGS.some(setting => setting.name === path[2])) return BOOLEAN_VALUES
  return []
}

export function apply(ctx: Context): void {
  ctx.inject(['commands'], registerCodexCommand)
  ctx.inject(['tuiCommandTrees'], registerTuiCommandTree)
}

function registerTuiCommandTree(ctx: Context): void {
  const tui = ctx as TuiContext
  const disposeTree = tui.tuiCommandTrees.register({
    root: 'codex',
    descriptions: { en: 'Manage the OpenAI Codex account and provider settings',
                    zh: '管理 OpenAI Codex 账号与提供方设置' },
    children: codexSubcommands,
  })
  ctx.provide('openAICodexTui', {} as TuiMarkerRuntime)
  ctx.effect(() => disposeTree, 'OpenAI Codex TUI completion adapter')
}
```

**Flow:** bundle load → `apply` publishes two independent injections; hosts without dsh-tui never resolve `tuiCommandTrees`, so only the executable command registers and `ctx.get('openAICodexTui')` stays `undefined`; a host with the runtime receives the tree provider whose `children` is consulted per keystroke with the canonical path — depth 1 yields the six actions (`status/login/logout/usage/config/set`), depth 2 under `set` yields the four settings keys, depth 3 under a known key yields `on/off`, anything else yields `[]`.
**Invariant:** the command handler never imports or requires the completion tree — the two registrations share only the root word `'codex'`; the path responder is total and fail-quiet (unknown paths/deeper levels return an empty list rather than throwing); the third-level gate re-validates the setting name against `CODEX_SETTINGS` so stale completions cannot appear after the table changes; the `openAICodexTui` marker is provided ONLY when a tree runtime exists (it is the host's detection signal) and disposal is effect-owned in both registrations.
**Probe:** `tests/tui.spec.ts:50-61` asserts registration without dsh-tui leaves `ctx.get('openAICodexTui')` undefined; `:63-114` provides a recording `tuiCommandTrees` fake and pins `children(['codex'])` → the exact six names, `children(['codex','set'])` → the four settings, `children(['codex','set','native-compaction'])` → `['on','off']`, plus zh root description `'管理 OpenAI Codex 账号与提供方设置'`. Executed green this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.tui\\.(codexSubcommands|registerTuiCommandTree|translatedNode)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 3, has_more false.

## Verdict
Adopt capability-optional dual registration with a pure canonical-path children function and structurally paired locale strings. Adapt the depth grammar to your command shape and the marker service name. Omit making the executor depend on completion metadata, or letting unknown completion paths throw. Coverage: src/tui.ts, tests/tui.spec.ts `no_recorded_issue` + `metadata_match`.
