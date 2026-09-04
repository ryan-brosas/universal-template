<!-- capsule-v2 -->
# Git install-spec classification ladder — how do you accept `github:user/repo`, scp-SSH, and full URLs without letting shell metacharacters through?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** One install command accepts npm specs and five shapes of git URLs; how does the parser decide which validator and which bun-installable form to produce?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/git-url.ts:parseGitUrl` (:292-358) with `tryNamespacedShorthand` (:240-270), `splitRef` (:119-167), `tryKnownHostSource` (:170-186), `parseGenericGitUrl` (:188-233); validators in `plugins/manager.ts` — `validatePackageName`/`validateGitSpec`/`gitInstallSpec`/`findGitPackageName` (:39-96).
**Signature:** `parseGitUrl(source): GitSource | null` where `GitSource = { type:"git", repo, host, path, ref?, pinned }`; `pinned = Boolean(ref)` drives "won't be auto-updated".
**Data Shape:** `SHORTHAND_PREFIXES: {github→github.com, gitlab, bitbucket, codeberg, sourcehut/srht→git.sr.ht}`; `SHORTHAND_RE = /^([a-z]+):([^/:#]+)\/([^#]+?)(?:\.git)?(?:#(.+))?$/i` — non-greedy repo so `.git` and `#ref` bind tightly and nested GitLab groups work.

### Decisive source
```ts
const shorthand = tryNamespacedShorthand(trimmed);       // 1. github:user/repo#ref
if (shorthand) return shorthand;
const stripped = /^git\+/i.test(trimmed) ? trimmed.slice(4) : trimmed; // 2. git+ scheme strip
const hasGitPrefix = /^git:(?!\/\/)/i.test(stripped);    // 3. bare git: shorthand gate
// Accept ONLY protocol URLs or scp-like SSH without the prefix:
if (!hasGitPrefix && !/^(https?|ssh|git):\/\//i.test(url) && !/^git@[^:]+:.+\/.+/i.test(url)) return null;
...
return parseGenericGitUrl(url);                          // 5. any-host fallback (requires dotted host)
```
**Flow:** namespaced shorthand → `git+` strip → `git:` prefix strip → acceptance gate → hash decodeURIComponent check (reject malformed %-encodings) → `splitRef` peels `@ref` from scp-like/URL/bare forms → known-host candidates (scp converted to https for matching; credentials stripped from http(s) repo URLs) → generic fallback. Manager-side split: specs that parse as git get `validateGitSpec` (reject `[;&|`$(){}<>\\\n\r\t]`) while everything else gets the strict npm `VALID_PACKAGE_NAME` regex — two validators because git specs legitimately contain `:/#+@`.
**Invariant:** classification is ordered and total — unknown input throws with a suggestion ("Did you mean './x' or 'owner/repo'?"); ref extraction never trusts URL hash blindly (decode check); `findGitPackageName` matches installed deps by host+path identity, NOT ref, so a failed ref-to-ref upgrade still resolves the original package name. Bun's DependencyLoop on same-repo ref replacement is dodged by removing only the stale manifest edge before install (rollback restores it).
**Probe:** anchor-greps at pin: `const SHORTHAND_RE = /^([a-z]+):([^/:#]+)\/([^#]+?)(?:\.git)?(?:#(.+))?$/i;` git-url.ts:49; direct-test seam: `test/plugin-install-validation.test.ts` "restores the previous git plugin tree when reinstalling a different ref fails validation" (:269).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.git-url.parseGitUrl" });
```

## Verdict
Adopt: the ordered classification ladder with an early cheap gate (`[a-z]+:[^/]`) that keeps protocol URLs out of the shorthand path; per-family validators instead of one permissive regex; repo-identity (not spec-string) matching when correlating installed deps. Adapt: your host table. Omit: sourcehut/codeberg entries if unneeded.
