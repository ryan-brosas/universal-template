<!-- capsule-v2 -->
# SUPERVISOR.md prompt override ladder — how is a fixed judge persona made project-customizable?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What is the discovery order for custom system prompts, and which built-in sections are contractually load-bearing?

## loadSystemPrompt (`src/core/prompt-loader.ts`)
**Path/Symbol:** `src/core/prompt-loader.ts:loadSystemPrompt` (:113-125), `BUILTIN_SYSTEM_PROMPT` (:18-105).
**Signature:** `loadSystemPrompt(cwd: string): {prompt: string, source: string}` — source is the winning path or the literal 'built-in'.
**Data Shape:** Ladder: `<cwd>/.pi/SUPERVISOR.md` → `<agentDir>/SUPERVISOR.md` → built-in template. Files are `.trim()`ed; no merging — whole-file replacement only.

### Decisive source
```ts
const projectPath = join(cwd, CONFIG_DIR, SUPERVISOR_MD);      // .pi/SUPERVISOR.md
if (existsSync(projectPath)) return { prompt: readFileSync(projectPath,'utf-8').trim(), source: projectPath };
const globalPath = join(getAgentDir(), SUPERVISOR_MD);
if (existsSync(globalPath))   return { prompt: ..., source: globalPath };
return { prompt: BUILTIN_SYSTEM_PROMPT, source: 'built-in' };
```
Built-in sections pinned by tests: idle MUST choose done/steer (`WHEN THE AGENT IS IDLE`), steering rules incl. "Never repeat a steering message that had no effect", CHEATING PREVENTION (5 named patterns: Unverified Claims / Test Manipulation / Metric Gaming / Short-Circuiting / Contradictions + "DO NOT accept done" + "Log the pattern in ASI"), CLOSING THE ASI LOOP (asi REQUIRED when steering), strict JSON response schema.

**Flow:** loaded FRESH on every analyze call (no caching) — editing SUPERVISOR.md takes effect next turn. The loader is called inside `analyze` before each judge invocation.
**Invariant:** (1) Project overrides global overrides built-in; there is NO partial merge, so custom files must restate critical sections. (2) `source` is returned for UI/tests because behavior differences must be attributable. (3) The built-in's cheating-prevention + ASI-loop sections are not decoration — prompt-builder's pattern summary and parser's ASI passthrough depend on the model emitting `asi`.
**Probe:** `tests/engine.test.ts` — `returns built-in prompt when no files exist` (:33), `loads project SUPERVISOR.md when it exists` (:43), `prefers project over global` (:67), `built-in prompt includes cheating prevention section` (:76), `built-in prompt includes ASI loop section` (:90).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "loadSystemPrompt SUPERVISOR.md BUILTIN_SYSTEM_PROMPT existsSync", limit: 8 });
```

## Verdict
Adopt the 3-rung whole-file override ladder + fresh-load-per-analysis. Adapt file names/locations to your host convention. Omit pi's getAgentDir; any two-tier path works.
