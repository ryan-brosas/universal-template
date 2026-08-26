<!-- capsule-v2 -->
# Persona resolution — embedded-defaults + user-override ladder with frontmatter tool/sandbox metadata

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I ship batteries-included agent personas yet let users override any of them by dropping a file in a config dir — and how do per-persona tool policies resolve?

## Config-dir-first load over Bun-embedded AGENTS.md files
**Path/Symbol:** `src/agent/persona.ts:loadPersona` (:119–158), `parsePersonaMetadata` (:70–111), `listPersonas` (:160–183), `resolveAgentConfig` (:206–280).
**Signature:** `async function loadPersona(name: string, optionsOrBaseDir?: LoadPersonaOptions | string): Promise<Persona>`; `function parsePersonaMetadata(content: string): PersonaMetadata`.
**Data Shape:** Persona = `{ name, systemPrompt, path, tools?: string[]|'all', defaultSandbox?, metadata? }`; frontmatter is a scalar-only YAML subset (`key: value`, `#` comments skipped); `tools:` accepts `none`→`[]`, `all`→`'all'`, or csv list.

### Decisive source
```ts
const configDirPath = join(getPersonaDir(name, options.baseDir), 'AGENTS.md');
if (await configFile.exists()) { /* user override wins: parse frontmatter, return */ }
// Otherwise use the embedded (batteries-included) persona.
const embedded = await readEmbeddedPersona(name);
if (embedded !== undefined) { /* same shape, path = embedded file */ }
throw new Error(`Persona not found: ${name} (expected ${configDirPath}, or a bundled persona of that name)`);

// Reasoning precedence: -r flag, then the model/alias hint, then config
// (REASONING / <BACKEND>_REASONING), then the backend default. Personas
// intentionally have no reasoning tier — reasoning follows the model, not
// the persona.
const reasoning = options.reasoning ?? options.aliasReasoning ?? resolveReasoning({ backend, globalConfig });
```

**Flow:** explicit `--system-prompt` short-circuits personas entirely → config-dir `AGENTS.md` beats embedded → embedded map (Bun `with { type: 'file' }` imports compiled into the binary) → throw with the expected path. Sandbox ladder: flag > persona frontmatter > global default > `read-only`. Tool ladder: `--no-tools` > `--tools` > persona frontmatter > `[]`; frontmatter `'all'` converts to `undefined` (full toolset — see tool-policy-duality).
**Invariant:** Reasoning is deliberately NOT persona-scoped ("reasoning follows the model, not the persona") — a porter adding per-persona reasoning breaks the alias-hint chain. `listPersonas` unions embedded+config names sorted, tolerating an absent config dir; unknown persona = loud error naming both lookup locations.
**Probe:** `tests/agent/persona.test.ts` (:59–240) — `loads persona tool policy per persona`, `returns embedded personas even for non-existent config directory`, `explicit reasoning takes precedence over alias reasoning`, `noTools flag forces an empty allowlist even when tools are opted in`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "loadPersona EMBEDDED_PERSONA_PATHS parsePersonaMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the override-over-embedded ladder and the "no persona-scoped reasoning" rule. Adapt the embedding mechanism (Bun file imports) to your bundler's asset inlining, and the four bundled personas to your own. Omit the frontmatter fields you don't enforce — unknown keys are already ignored by design.
