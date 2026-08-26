<!-- capsule-v2 -->
# Item Address Scheme Dispatch — given any item string, which transport owns it?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** In what order must a client classify an arbitrary item reference (URL, local path, `@ns/item`, GitHub `owner/repo/item[#ref]`, bare name) so lookalike inputs can't be hijacked by the wrong transport?

## Discriminated-union dispatch with security-first ref validation
**Path/Symbol:** `packages/shadcn/src/registry/address.ts:13-82` (`ResolvedItemAddress`, `resolveItemAddress`, `isGitHubItemAddress`), `:84-118` (`resolveGitHubRegistrySource`), `:124-182` (patterns + `isValidGitHubRef`); `utils.ts:273-275` (`isLocalFile`); `parser.ts:2-24`.
**Signature:** `resolveItemAddress(address: string): ResolvedItemAddress` — union of `{scheme:"url",url}` | `{scheme:"file",path}` | `{scheme:"namespace",namespace,item}` | `{scheme:"github",owner,repo,item,ref?}` | `{scheme:"shadcn",item}`.
**Data Shape:** GitHub owner pattern `/^(?!.*--)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/` (no leading/trailing hyphen, no `--`, ≤39 chars); repo pattern `[a-zA-Z0-9._-]+` minus `.`/`..`; ref rejects control chars, whitespace, and leading `-`.

### Decisive source
```ts
export function resolveItemAddress(address: string) {
  if (isUrl(address))    return { scheme: "url",   url: address }
  if (isLocalFile(address)) return { scheme: "file", path: address }
  const { registry, item } = parseRegistryAndItemFromString(address)
  if (registry) return { scheme: "namespace", namespace: registry, item }
  const githubAddress = resolveGitHubItemAddress(address)
  if (githubAddress) return githubAddress
  return { scheme: "shadcn", item: address }
}

// utils.ts — the ordering trap:
export function isLocalFile(path: string) {
  return path.endsWith(".json") && !isUrl(path)
}
```

**Flow:** URL → local `.json` file → `@namespace/item` (regex `/^(@[a-zA-Z0-9](?:[a-zA-Z0-9-_]*[a-zA-Z0-9])?)\/(.+)$/`: namespace needs ≥2 chars with alnum ends; unmatched `@…` degrades to shadcn scheme) → GitHub `owner/repo/item...[#ref]` (≥3 segments, owner/repo validated, invalid ref THROWS `RegistryValidationError` rather than falling through) → bare-name default. Namespace check runs BEFORE GitHub so `@acme/ui` is never misread as owner/repo.
**Invariant:** The dispatch order is the contract. Because `.json` wins over GitHub, `owner/repo/data/schema.json` is a FILE address even though it looks like a GitHub path (test-pinned). Refs starting with `-` are rejected outright — this blocks git-option injection like `--upload-pack=/bin/false` at the parsing layer, before any subprocess or network use.
**Probe:** `packages/shadcn/src/registry/address.test.ts` — `:97-112` asserts six invalid-GitHub shapes (`foo/bar`, `-owner/repo/button`, `owner-/repo/button`, `owner/./button`, `owner/../button`, space-in-repo) fall back to `scheme:"shadcn"`; `:114-119` pins the `.json`-beats-GitHub rule; `:139-143` + `:169-173` pin rejection of `#--upload-pack=/bin/false`. Runner absent in checkout — pinned by direct test read.
**Coverage:** address.ts, parser.ts, utils.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "resolveItemAddress scheme github namespace url file", limit: 10 });
```

## Verdict
Adopt the five-scheme union and its exact precedence (url > .json-file > @namespace > github > default) plus the dash-leading-ref rejection as a unit. Adapt scheme vocabulary to your domain; keep validation failures LOUD (throw) instead of silently reclassifying a malicious-looking ref. Omit the GitHub raw-content reader itself (separate plane).
