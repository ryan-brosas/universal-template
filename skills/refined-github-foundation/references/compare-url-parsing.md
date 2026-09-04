<!-- capsule-v2 -->
# Compare-URL Parsing — how do you decode `compare/base...head` where the head side has 1–3 slash-separated components?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What are the assignment rules for `user:repo:branch` heads and when is it cross-repo?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/parse-compare-url.ts:parseCompareUrl` (:18–47).
**Signature:** `parseCompareUrl(pathname: string): Comparison | undefined` with `Comparison = {head:{repo,branch}, base:{repo,branch}, isCrossRepo}`.
**Data Shape:** input regex `/compare[/](?<baseBranch>[^.]+)[.][.][.]?(?<heads>.+)/` — accepts both `..` (two-dot, commits-only) and `...` (three-dot) separators.

### Decisive source
```ts
const {baseBranch, heads} = match.groups!;
const headParts = heads.split(':');
const headBranch = headParts.pop()!;              // Branch is always last, or the only one
const headOwner = headParts.shift() ?? base.owner; // The owner is first, or it's the same as the base
const headName = headParts.pop() ?? base.name;     // The repo is first or middle, or it's the same as the base
if (headParts.length > 0) throw new Error('Invalid compare URL format');
```

**Flow:** getRepo(pathname) supplies base context → regex must match else `undefined` → split head side on `:` → pop = branch (last), shift = owner (first), pop = name (middle/second), leftovers ⇒ throw → `isCrossRepo` = headOwner !== base.owner || headName !== base.name.
**Invariant:** the pop/shift/pop ORDER encodes GitHub's grammar precisely: `branch`, `owner:branch`, `repo:branch`, `owner:repo:branch` are all legal; anything longer is invalid rather than best-effort. Two-dot compares parse identically but semantically differ (direct commit range) — this function intentionally does NOT distinguish them; porters adding semantics must re-check.
**Probe:** `source/github-helpers/parse-compare-url.test.ts:9` ('parseCompareUrl') pins all four head shapes + non-compare URLs returning undefined.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "parseCompareUrl compareRegex headOwner headName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim for any `range-spec` URL grammar with optional namespace prefixes. Adapt separator characters. Keep the strict leftover-throw. Direct test present.
