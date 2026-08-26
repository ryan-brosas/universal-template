<!-- capsule-v2 -->
# Skill scope auto-resolution — content classifier routes new skills to global or project

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** When an agent saves a procedure without an explicit scope, how do you decide "global knowledge" vs "repo-specific" from the skill text itself — without asking the user and without a model call?

## Scope auto-resolution
**Path/Symbol:** `src/store/skill-store.ts` — `SkillStore.resolveScope` (:718–739), `getScopeRoot` (:741–743), `create` call site :380; direct tests `tests/store/skill-store.test.ts:110–135` (`classifies transferable procedures as global by default`, `classifies repo-specific procedures as project by default`).
**Signature:** `resolveScope(scope: SkillScope | undefined, name: string, description: string, body: string): SkillScope`.
**Data Shape:** returns `"project"` only when a project context exists AND the signal vote crosses a threshold; otherwise `"global"`. Haystack = `` `${name}\n${description}\n${body}`.toLowerCase() ``.

### Decisive source
```ts
// resolveScope (718-739)
if (scope) return scope;                                    // explicit always wins
if (!this.projectSkillsDir || !this.projectName) return "global"; // no project → global

const haystack = `${name}\n${description}\n${body}`.toLowerCase();
const projectLower = this.projectName.toLowerCase();

const strongSignals = [
  haystack.includes(projectLower),                          // mentions the active project by name
  /\bthis repo\b|\bthis repository\b|\bthis project\b|\bour codebase\b|\bour app\b/.test(haystack),
  /\bpackage\.json\b|\bpnpm-lock\.yaml\b|\byarn\.lock\b|\btsconfig\.json\b|\bdocker-compose(\.ya?ml)?\b|\b\.env(\.[a-z0-9._-]+)?\b/.test(haystack),
  /(^|\s)(src|app|apps|packages|services|scripts|tests|docs|infra|migrations|db|api|web|frontend|backend)\/[a-z0-9._/-]+/m.test(haystack),
  /\b(npm|pnpm|yarn|bun)\s+(run|test|build|dev|lint|deploy)\b/.test(haystack),
].filter(Boolean).length;

const weakerSignals = [
  /\bdeploy\b|\brelease\b|\bmigrate\b|\bmonorepo\b|\bworkspace\b|\bstaging\b|\bproduction\b/.test(haystack),
  /\bteam convention\b|\bcodebase convention\b|\brepo convention\b/.test(haystack),
].filter(Boolean).length;

return strongSignals >= 2 || (strongSignals >= 1 && weakerSignals >= 1) ? "project" : "global";
```

**Flow:** (1) Explicit scope parameter short-circuits everything. (2) No bound project (null dir/name) forces global — project skills are impossible without a target root. (3) Otherwise five STRONG signals vote on the haystack: project-name mention, deictic repo references ("this repo"), repo-config filenames, repo-directory paths (`src/...` style with word-boundary prefix so `docs/` inside prose still matches via `(^|\s)`), and package-manager invocations. (4) Two WEAK signals (deploy-lifecycle vocabulary, team-convention phrases) can reinforce but never alone decide. (5) Threshold grammar: ≥2 strong, OR ≥1 strong + ≥1 weak → project; anything else → global.

**Invariant:** the DEFAULT is global — ambiguity resolves toward the more portable scope because global skills remain visible in every project while a wrongly-project skill becomes invisible outside it (asymmetric cost). Weak signals alone NEVER produce project scope (a generic "deploy to staging" procedure stays global). The signal lists are pure regex over lowercased free text: no file I/O, no LLM round-trip, deterministic for identical input. Direct tests pin both directions of the threshold ("transferable procedures" → global, "repo-specific procedures" → project).

**Probe:** `tests/store/skill-store.test.ts` — `classifies transferable procedures as global by default` (:110), `classifies repo-specific procedures as project by default` (:123), `does not allow project scope without an active project` (:224). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "resolveScope strongSignals weakerSignals haystack", limit: 5 });
// live-verified rank-1 sole hit total:1: SkillStore.resolveScope :718-739
```

## Verdict
Adopt the voting-classifier shape (explicit override → context availability gate → strong/weak regex vote → conservative default). Adapt the keyword lists to your host's ecosystem vocabulary. Omit the weak-signal tier if you want a simpler ≥2-strong rule — but keep the conservative-default asymmetry: misrouting to global costs visibility, misrouting to project costs correctness.
