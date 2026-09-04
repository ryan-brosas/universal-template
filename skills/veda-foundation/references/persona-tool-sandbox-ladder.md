<!-- capsule-v2 -->
# Persona tool/sandbox resolution ladder — how do CLI flags, persona frontmatter, and config compose into one effective (tools, sandbox) pair?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** In what exact order must persona frontmatter, explicit flags, and global config resolve for tools and sandbox — and where is the tri-state policy born?

## resolveAgentConfig precedence kernel
**Path/Symbol:** `src/agent/persona.ts` : `resolveAgentConfig` (:206-281); frontmatter loader `loadPersona` (:119-160) attaches `tools` + `defaultSandbox`.
**Signature:** `async function resolveAgentConfig(options: ResolveConfigOptions, defaults: { persona: string }, globalConfig?: GlobalConfig): Promise<AgentConfig>`.
**Data Shape:** `Persona.tools?: string[] | 'all'` (frontmatter), `ResolveConfigOptions.tools?: string[]`, `.noTools?: boolean`; output `AgentConfig.tools?: string[]` — the tri-state where `undefined` = full backend toolset, `[]` = none.

### Decisive source
```ts
// Reasoning precedence: -r flag, then the model/alias hint, then config
// ..., then the backend default. Personas intentionally have no reasoning tier.
const reasoning = options.reasoning ?? options.aliasReasoning ?? resolveReasoning({...});

// Sandbox precedence: explicit --sandbox flag, then persona frontmatter
// sandbox:, then the config DEFAULT_SANDBOX, then read-only.
const sandbox = options.sandbox ?? personaSandbox ?? globalConfig?.defaultSandbox ?? 'read-only';

// Tool policy. undefined means "backend's full toolset" (worker's tools: all);
// [] means "no tools"; a list is an explicit allowlist.
// Precedence: --no-tools > --tools > persona frontmatter > no tools.
let tools: string[] | undefined;
if (options.noTools) {            tools = [];
} else if (options.tools) {       tools = options.tools;
} else if (personaTools === undefined) { tools = [];       // NO frontmatter → no tools
} else if (personaTools === 'all') {     tools = undefined; // 'all' → tri-state undefined
} else {                          tools = personaTools; }
```

**Flow:** sandbox ladder has FOUR rungs ending in a safe read-only default; tool ladder converts the persona's `'all'` literal into the tri-state `undefined` while a MISSING frontmatter key becomes `[]` (deny-by-default — an agent without declared tools gets none). Reasoning deliberately skips the persona entirely ("reasoning follows the model, not the persona") and accepts an alias-injected hint as its second rung. The resolved pair feeds straight into `withSandboxModeNotice(systemPrompt, { tools, sandbox })` so prompt text mirrors runtime reality.
**Invariant:** `personaTools === undefined` (key absent) and `personaTools === 'all'` must map to OPPOSITE outcomes (`[]` vs `undefined`) — collapsing them either bricks the agent or silently grants everything; this is the same empty-vs-undefined duality the pi mapper and notice selector consume downstream. Drift commit 2f9de50 flipped the worker persona to `sandbox: full` making the undefined path the worker's production default.
**Probe:** `tests/agent/persona.test.ts` (:1-571; worker fixture pins `---\ntools: all\nsandbox: full\n---`) — run `bun test tests/agent/persona.test.ts` (57 assertions green at pin).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"resolveAgentConfig persona sandbox precedence","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.agent.persona.resolveAgentConfig AsyncFunction src/agent/persona.ts`.

## Verdict
Adopt both ladders and the deny-by-default missing-key rule verbatim. Adapt flag names/config keys. Omit the Bun-embedded persona file mechanism if your host loads personas from disk only — but keep user-override-over-embedded precedence (`loadPersona` checks config-dir AGENTS.md BEFORE embedded copies).
