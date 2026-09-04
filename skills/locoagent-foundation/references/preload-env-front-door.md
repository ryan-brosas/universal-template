<!-- capsule-v2 -->
# Preload env + provider front door — how does a fork remap env variables and pin a CLI before any module reads them?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a CLI fork must let users configure an OpenAI-compatible provider with friendly `LLM_*` names instead of the confusing `OPENAI_*` internals, and must attach to an isolated browser profile from any cwd, where does that wiring run so it is in place before first use?

## bunfig preload macro-stub: env load, provider translation, CDP pin, argv injection
**Path/Symbol:** `stubs/globals.ts` (whole file :1-104); wired by `bunfig.toml` `[run] preload = ["./stubs/globals.ts"]` (:1-2). Functions: `normalizeProviderEnv` (:41-72), top-level env loader (:10-29), CDP pin (:83-86), argv inject (:89-94), `globalThis.MACRO` (:96-104).
**Signature:** `normalizeProviderEnv(): void` — reads `process.env.LLM_PROVIDER/LLM_API_KEY/LLM_MODEL/LLM_BASE_URL`, writes legacy vars, sets `CLAUDE_CODE_USE_OPENAI`.
**Data Shape:** `.env` file at `<root>/.env` parsed into `process.env` (blank values SKIPPED); provider presets `{ deepseek: 'https://api.deepseek.com', openai: 'https://api.openai.com/v1' }`; `AGENT_BROWSER_CONFIG` pinned to `<root>/agent-browser.json` only if not already set.

### Decisive source
```ts
// Blank value (e.g. `CHROME_WORK_PROFILE=`) is a "leave for the default" placeholder,
// NOT a real setting. Injecting '' defeats every `env.X ?? default` downstream
// (??/|| treat '' as set) — a blank CHROME_WORK_PROFILE crashed setup-chrome with mkdirSync('').
if (key && val && !(key in process.env)) process.env[key] = val

function normalizeProviderEnv() {
  const provider = (process.env.LLM_PROVIDER ?? '').trim().toLowerCase()
  ...
  if (provider === 'anthropic') {
    if (provider) process.env.CLAUDE_CODE_USE_OPENAI = ''      // native SDK path — shim OFF
    setIfUnset('ANTHROPIC_API_KEY', apiKey)
    setIfUnset('ANTHROPIC_MODEL', model)
  } else {
    if (provider) process.env.CLAUDE_CODE_USE_OPENAI = '1'     // OpenAI-compatible shim ON
    setIfUnset('OPENAI_API_KEY', apiKey); setIfUnset('OPENAI_MODEL', model)
    setIfUnset('OPENAI_BASE_URL', baseUrl || PRESET_BASE[provider] || '')
  }
}
// CDP pin: point AGENT_BROWSER_CONFIG at project agent-browser.json so every
// agent-browser invocation attaches to the isolated profile, not its own bundled
// "Chrome for Testing". Guarded on existsSync; explicit user override wins.
if (existsSync(agentBrowserPin) && !process.env.AGENT_BROWSER_CONFIG) process.env.AGENT_BROWSER_CONFIG = agentBrowserPin
// SKIP_PERMISSIONS=1 → inject --dangerously-skip-permissions into argv
```

**Flow:** preload runs once at startup → parse `.env` (skip comments/blank lines and **blank values**) → if any `LLM_*` is set, translate to legacy vars via `setIfUnset` (explicit legacy always wins) and toggle `CLAUDE_CODE_USE_OPENAI` by provider → pin `AGENT_BROWSER_CONFIG` to the project config (existsSync-guarded) → optionally append `--dangerously-skip-permissions` to `process.argv`.
**Invariant:** The preload must be the FIRST thing that runs, so the mapping and pin exist before any module reads `process.env` or spawns `agent-browser`. Blank `.env` values are "leave default" placeholders and MUST be skipped (injecting `''` breaks every `??`/`||` default — this is a real crash that happened). `setIfUnset` makes the mapping non-destructive: an explicitly-set legacy var always wins, so power users are unaffected. `CLAUDE_CODE_USE_OPENAI` is toggled ONLY by the explicit `LLM_PROVIDER` choice — it is the authoritative switch.
**Probe:** No direct test exists for `stubs/globals.ts` (coverage caveat — behavior is source-grounded). Deterministic probes: grep-pinned comment :20-24 (blank-value crash rationale), :37-40 (non-destructive mapping), :79-82 (CDP-pin rationale), :88-94 (argv inject); `search_graph` resolves `normalizeProviderEnv` `stubs.globals` :41-72; `bunfig.toml` `[run] preload` confirmed on disk.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "normalizeProviderEnv LLM_PROVIDER CLAUDE_CODE_USE_OPENAI preload", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the preload-stub pattern (env loader + provider front door + CLI pin + argv inject in one startup hook), the blank-value-skip rule, `setIfUnset` non-destructive remapping, and the existsSync-guarded pin. Adapt the `.env` path, preset base URLs, provider names, and CLI flag. Omit the hard-coded `MACRO` version/build metadata unless your build needs it. Coverage caveat: no direct test; behavior source-grounded.
