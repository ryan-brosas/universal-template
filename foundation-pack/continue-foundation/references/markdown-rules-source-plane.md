<!-- capsule-v2 -->
# Markdown rule-source plane — where does rule text enter the config, and what order wins?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you aggregate rules from agent files, .continue dirs, and colocated rules.md files into ONE ordered list with a mutable cache that file watches keep fresh?

## Unshift-assembled precedence + watch-driven singleton cache
**Path/Symbol:** `core/config/profile/doLoadConfig.ts:loadRules` (40–62, unshift into `newConfig.rules` at 155); `core/config/markdown/loadMarkdownRules.ts:loadMarkdownRules` (15–105); `core/config/markdown/loadCodebaseRules.ts` (CodebaseRulesCache 10–62, loader 67–129); `core/config/markdown/loadMarkdownSkills.ts` (13–112).
**Signature:** `loadMarkdownRules(ide): Promise<{rules: RuleWithSource[]; errors}>` ; `CodebaseRulesCache.getInstance() / refresh(ide) / update(ide, uri) / remove(uri)` ; `loadMarkdownSkills(ide): Promise<{skills: Skill[]; errors}>`.
**Data Shape:** every rule carries `source` ("agentFile" | "rules-block" | "colocated-markdown"), `sourceFile`, optional frontmatter (`name`, `description`, globs, `alwaysApply`, `invokable`).

### Decisive source
```ts
// loadRules: successive UNSHIFTs => LAST unshift lands FIRST in final order
rules.unshift(...yamlRules);            // .continuerules dotfiles
rules.unshift(...markdownRules);        // .continue/rules + .continue/prompts (+ agent files inside)
rules.unshift(...codebaseRulesCache.rules);   // colocated rules.md cache wins the head
// ...later: newConfig.rules.unshift(...rules) puts ALL of these ahead of yaml-plane assistant rules

// agent-file priority (inside loadMarkdownRules): fixed order, first hit wins per workspace,
export const SUPPORTED_AGENT_FILES = ["AGENTS.md", "AGENT.md", "CLAUDE.md"];
// first workspace with any agent file wins; pushed with alwaysApply: true, source: "agentFile"

// invokable markdown rules are EXCLUDED from rules here; doLoadConfig converts them to slash commands:
if (!rule.invokable) rules.push({ ...rule, source: "rules-block", sourceFile: file.path });

// CodebaseRulesCache: private-constructor singleton; upsert by sourceFile on update(uri)
const matchIdx = this.rules.findIndex((r) => r.sourceFile === uri);
if (matchIdx === -1) this.rules.push(ruleWithSource); else this.rules[matchIdx] = ruleWithSource;
```

**Flow:** startup walkDir → `CodebaseRulesCache.refresh()` → `reloadConfig("Initial codebase rules post-walkdir/load reload")` (fire-and-forget chain in core.ts:247–257). On each load, loadRules assembles dotfiles→markdown→cache via unshifts (final head-order: colocated cache > .continue/rules+prompts > .continuerules), then doLoadConfig unshifts the whole block ahead of yaml-plane rules. File watches: created/removed colocated rules mutate the cache FIRST (`update`/`remove`) THEN trigger reloadConfig — ordering guarantees reload reads fresh state. Skills load separately: SKILL.md under `.continue/skills` (global+workspace) PLUS `.claude/skills` dirs; zod-validates frontmatter `{name ≥1, description ≥1}`; sibling files walked minus SKILL.md attach as `files`.
**Invariant:** parse errors anywhere in this plane are NON-fatal (collected per-file/per-dir into errors); invokable rules appear exactly once in the system (as slash commands, never also as rules); colocated rules scoped by parent dir via `markdownToRule(content, opts, parentDir)`.
**Probe:** no direct suite for the core loaders at this pin (runner block; CLI twin `extensions/cli/src/util/loadMarkdownSkills.test.ts` exists but is out of lane scope). Source-pinned observable: doLoadConfig.vitest.ts:43–48 mocks both markdown modules, confirming they are load-path dependencies of every compile.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "loadMarkdownRules CodebaseRulesCache loadMarkdownSkills", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.profile.doLoadConfig.loadRules", direction: "outbound", depth: 2 });
// observed callees: getWorkspaceContinueRuleDotFiles, loadMarkdownRules, CodebaseRulesCache.getInstance
```

## Verdict
Adopt unshift-assembled precedence (or document an explicit priority array) plus an upsert-by-path singleton cache mutated before reload for filesystem-sourced prompt/rules text; adapt source names, agent-file priority list, and skill frontmatter schema to your host; omit the .claude/skills compatibility dir unless you need cross-tool interop.
