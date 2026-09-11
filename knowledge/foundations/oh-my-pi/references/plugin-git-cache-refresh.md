<!-- capsule-v2 -->
# Bun git-cache refresh — why does re-installing an existing git plugin pin the OLD ref, and how is that fixed?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** `bun install github:user/repo#v2` is a no-op when the lockfile already pins that package — how do you force the pin to actually move?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/bun-git-cache.ts:refreshBunGitCache` (:48-91) + `normalizeRepositoryUrl` (:29-45) + `runCommand` (:13-27); call site `manager.ts:PluginManager.install` Step 2 (:546-571).
**Signature:** `refreshBunGitCache(source: GitSource, cwd: string): Promise<void>`; `normalizeRepositoryUrl(repo): string` canonicalizes scp-like and URL forms to one comparable shape.
**Data Shape:** bun's bare-clone cache = `<bun pm cache>/*.git` directories, each with a real git `remote.origin.url`; match key is the NORMALIZED repo URL (lowercased host, trailing `.git` and slashes stripped, `git+`/`#ref` removed, `git@host:path` → `ssh://host/path`).

### Decisive source
```ts
const cacheResult = await runCommand(["bun", "pm", "cache"], cwd); // ask bun where clones live
...
for (const entry of entries) {
	if (!entry.isDirectory() || !entry.name.endsWith(".git")) continue;
	const originResult = await runCommand(["git", "-C", repositoryDir, "config", "--get", "remote.origin.url"], cwd);
	if (originResult.exitCode !== 0 || normalizeRepositoryUrl(originResult.stdout.trim()) !== repositoryUrl) continue;
	const fetchResult = await runCommand([
		"git", "-C", repositoryDir, "fetch", "--force", "--prune", "origin",
		"+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*",
	], cwd);
```
**Flow:** install detects "git spec AND package already present under another name/ref" → `refreshBunGitCache` fetches heads+tags force-pruned into every matching cached bare clone → then runs `bun update <actualName>` (not `install`) so bun re-resolves through the now-fresh clone → lockfile pin moves. First-time installs skip both steps because the initial `bun install` populated the cache from the remote. ENOENT cache dir → silent no-op return.
**Invariant:** without the forced fetch, `bun update` resolves refs against a stale cached clone and silently keeps the old commit (#3063, #5401); normalization must be symmetric (both sides through `normalizeRepositoryUrl`) or scp-vs-https duplicates never match. Every step throws on failure — a failed refresh aborts BEFORE `bun update`, inside the install transaction's rollback scope.
**Probe:** direct-test seam: `test/plugin-install-validation.test.ts` mocks `["bun","pm","cache"]` (`pmCacheSubprocess` :23-35) and asserts the follow-up command equals `["bun","update","git-plugin"]` (:323); anchor-grep at pin: `"+refs/heads/*:refs/heads/*",` bun-git-cache.ts:82.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.bun-git-cache.refreshBunGitCache" });
```

## Verdict
Adopt: identify package-manager-internal caches by querying the tool itself (`pm cache`) and matching normalized origin URLs before mutating them. Adapt: your PM's cache layout; keep the symmetric-normalization comparison. Omit: bun specifics if your tool has first-class `update --force`.
