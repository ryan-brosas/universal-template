<!-- capsule-v2 -->
# GitHub Ref Resolution Ladder — how do you turn `owner/repo#v1.2.0` into a pinned commit SHA with one network call, and what happens when git is unavailable?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** Given a possibly-shorthand GitHub ref (branch, tag, annotated tag, qualified ref, full SHA), what resolution order and fallbacks produce a deterministic SHA while keeping failure messages actionable?

## ls-remote candidate ladder + promise-cached resolution + authenticated mirror
**Path/Symbol:** `packages/shadcn/src/registry/github-ref.ts:resolveGitHubRef` (:31-55), `resolveGitHubRefUncached` (:57-110), `getPreferredGitHubRefNames` (:116-130), `parseGitLsRemote` (:132-148), `resolveGitHubRefWithAuth` (:150-203) wrapping `github-cli.ts:resolveGitHubRefViaAuth` (:415-476).
**Signature:** `resolveGitHubRef(address: GitHubSource, { cache?: Map<string, Promise<string>>, authAnchor?: object }): Promise<string>` (40-hex lowercase SHA); `getPreferredGitHubRefNames(ref): string[]`; `parseGitLsRemote(stdout): Map<ref, sha>`.
**Data Shape:** Cache key `${owner}/${repo}#${ref}` → promise of SHA. Candidate order for a shorthand ref: `[refs/heads/<r>, refs/tags/<r>^{}, refs/tags/<r>, <r>]`; explicit `refs/tags/…` prepends only the peeled form; `HEAD` stays bare.

### Decisive source
```ts
if (GITHUB_SHA_PATTERN.test(ref)) return ref.toLowerCase()   // zero-subprocess fast path

const cacheKey = `${address.owner}/${address.repo}#${ref}`
if (options.cache?.has(cacheKey)) return options.cache.get(cacheKey)!
const promise = resolveGitHubRefUncached(address, ref, options).catch((error) => {
  options.cache?.delete(cacheKey)          // evict so a retry can succeed
  throw error
})
options.cache?.set(cacheKey, promise)      // stored BEFORE awaiting

// one subprocess for ALL candidates:
execa("git", ["ls-remote", "--symref", "--", repoUrl, ...candidates],
      { env: { GIT_TERMINAL_PROMPT: "0" }, timeout: 15_000 })
// parse skips "ref:" symref lines, validates each sha against /^[a-fA-F0-9]{40}$/
for (const candidate of getPreferredGitHubRefNames(ref)) {
  const sha = refs.get(candidate)
  if (sha) return sha                      // branch beats peeled tag beats tag object
}
```

**Flow:** 40-hex input short-circuits (lowercased, no git at all) → otherwise a single `git ls-remote --symref` call advertises all candidates at once; preference walk picks branch > peeled annotated tag (`^{}`) > tag object > raw string → ls-remote FAILURE with an `authAnchor` (private repo ⇒ exit 128) falls back to the authenticated REST/gh resolver whose ordering MIRRORS git's: try `commits/heads/<r>` first, fall to `commits/tags/<r>` ONLY on HTTP 404 (non-404 is terminal), peel annotated tags via `git/tags/<sha>` bounded by TAG_DEREFERENCE_DEPTH=5 → ENOENT yields an install-git suggestion, execa timeouts yield a network suggestion.
**Invariant:** Resolution must be one subprocess per ref per invocation (cache shared command-locally across concurrent items); failed resolutions must not poison the cache; shorthand ambiguity must resolve identically whether git or the REST API did the resolving; GIT_TERMINAL_PROMPT must be 0 so a private repo fails fast instead of prompting.
**Probe:** `packages/shadcn/src/registry/github-ref.test.ts` — :20-41 exact argv/env/timeout; :43-52 SHA fast-path calls nothing; :54-61 candidate ladder order; :63-74 peeled-tag preference; :76-98 short SHA treated as ref name; :100-110 cache reuse (1 execa call); :112-130 rejection eviction then success (2 calls); :132-156 ENOENT/timeout suggestions. `github-cli.test.ts` :369-506 authenticated mirror matrix. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github-ref.ts + github-cli.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "resolveGitHubRef git ls-remote symref candidates peeled annotated tag parse", limit: 8 });
// observed: parseGitLsRemote #1 (:132-148), resolveGitHubRef #2 (:31-55),
// getGitHubRefCandidates #3 (:112-114)
```

## Verdict
Adopt the advertise-once/prefer-in-order pattern (one ls-remote for the whole candidate set, deterministic preference walk), the promise-cache-with-rejection-eviction wrapper, and the mirrored-order authenticated fallback for any git-host source resolver. Adapt the candidate list to your host's ref namespace and the depth bound to your tolerance for nested tag objects. Omit the gh subprocess rung if your REST fallback always has credentials.
