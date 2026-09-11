<!-- capsule-v2 -->
# Compound prefix collapse — word-aligned LCP for permission suggestions

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you turn N subcommand prefixes from a compound command into a minimal suggestion set users will accept?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/prefix.ts` — `getCompoundCommandPrefixesStatic(command, excludeSubcommand?)` (:135-175), `longestCommonPrefix` word-aligned (:182-204), `getCommandPrefixStatic` wrapper recursion (:28-70), `handleWrapper` (:72-121).
**Signature:** `getCompoundCommandPrefixesStatic(cmd) → string[]` — one collapsed prefix per root command.
**Data Shape:** prefixes grouped by first word; groups collapsed via WORD-boundary LCP (never mid-word).

### Decisive source
```ts
// Compute the longest common prefix of strings, aligned to word boundaries.
// e.g. ["git fetch", "git worktree"] → "git"
//      ["npm run test", "npm run lint"] → "npm run"
```

**Flow:** split compound into subcommands (heredoc-aware legacy splitter), skip excluded ones (e.g. read-only commands already auto-allowed), compute each one's prefix via spec-driven wrapper recursion (env-prefix prepended when envVars present; `nice`-style wrappers recurse into the wrapped command with wrapperCount ≤2, depth ≤10), then group by root word and collapse each group with the word-aligned LCP — `slice(0, max(1, shared))` guarantees at least the root word survives.

**Invariant:** (1) Collapse at WORD boundaries only: character-level LCP of `git fetch`/`git fish` would mint a broken rule. (2) At least one word always remains (`max(1, commonWords)`) — a suggestion must never be empty. (3) Exclusion lets callers suppress prefixes they already allow, keeping prompts minimal. (4) Wrapper recursion shares the security tier's budgets but serves the suggestion tier only.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'aligned to word boundaries' src/utils/bash/prefix.ts` → :178; `grep -nF 'wrapperCount > 2' src/utils/bash/prefix.ts` → :33; graph resolves buildPrefix via specPrefix.ts :88-137 and getCompoundCommandPrefixesStatic line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getCompoundCommandPrefixesStatic longestCommonPrefix getCommandPrefixStatic handleWrapper", limit: 5 });
```

## Verdict
Adopt for compound-command UX in any permission system: per-subcommand prefixes → root grouping → word-aligned LCP with the ≥1-word floor.
