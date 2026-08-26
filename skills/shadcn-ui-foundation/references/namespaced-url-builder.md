<!-- capsule-v2 -->
# Namespaced URL Builder — how does `@acme/button` become a real URL + headers from user config?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** Given a user config mapping `@acme` → a URL template (string or object with headers/params), what is the exact substitution order and the failure gates before any network call?

## Template substitution ladder with env-var suppression
**Path/Symbol:** `packages/shadcn/src/registry/builder.ts:22-146` (`buildUrlAndHeadersForRegistryItem`, `buildUrlFromRegistryConfig`, `buildHeadersFromRegistryConfig`, `appendQueryParams`, `shouldIncludeHeader`); `env.ts:3-8`; `validator.ts:40-50`.
**Signature:** `buildUrlAndHeadersForRegistryItem(name: string, config?: Config) => { url: string; headers: Record<string,string> } | null`; `expandEnvVars(value: string): string`.
**Data Shape:** Registry config per namespace is either a plain template string or `{ url, params?, headers? }`. Placeholders: `{name}` = item path, `{style}` = config style, `${VAR}` = environment variable. Builtin namespaces merge UNDER user config: `{...BUILTIN_REGISTRIES, ...config?.registries}`.

### Decisive source
```ts
// buildUrlAndHeadersForRegistryItem — dispatch + gates
let { registry, item } = parseRegistryAndItemFromString(name)
if (!registry) {
  if (isUrl(name) || isLocalFile(name) || isLocalPath(name) || isGitHubItemAddress(name)) {
    return null                    // caller owns raw addresses; not a registry lookup
  }
  registry = "@shadcn"             // bare names default to the builtin registry
}
const registries = { ...BUILTIN_REGISTRIES, ...config?.registries }
const registryConfig = registries[registry]
if (!registryConfig) throw new RegistryNotConfiguredError(registry)
validateRegistryConfig(registry, registryConfig)   // pre-flight missing ${VARS}

// buildUrlFromRegistryConfig — order matters:
let url = registryConfig.url.replace("{name}", item)
if (config?.style && url.includes("{style}")) url = url.replace("{style}", config.style)
baseUrl = expandEnvVars(baseUrl)                   // ${VAR} -> value || ""
// then appendQueryParams(): URLSearchParams over expanded param values,
// skipping empty ones; separator is "&" if baseUrl already contains "?"

// shouldIncludeHeader — suppress unexpanded secret templates
if (originalValue.includes("${")) {
  const envVars = originalValue.match(/\${(\w+)}/g)
  if (envVars) {
    const templateWithoutVars = originalValue.replace(/\${(\w+)}/g, "").trim()
    return trimmedExpanded !== templateWithoutVars   // expansion no-op => DROP header
  }
}
```

**Flow:** parse `@ns/item` → bare-name fallbacks (URL/local/github handled by callers via `null`) → namespace lookup with builtin merge → unknown namespace throws typed error → env-var pre-flight (`extractEnvVarsFromRegistryConfig` collects `${VAR}` from url+params+headers; any missing from context env → `RegistryMissingEnvironmentVariablesError` listing them) → `{name}` then conditional `{style}` replacement → env expansion (unset vars expand to empty STRING, never throw) → query params appended with existing-query detection.
**Invariant:** A header whose `${VAR}`s are ALL unset must NOT be sent (expansion would yield the literal template minus vars — e.g. `Bearer ` — leaking a malformed credential). Style substitution happens only when the placeholder exists AND config.style is set. Validation precedes URL construction so users see "set these vars" instead of a garbled request.
**Probe:** `packages/shadcn/src/registry/validator.test.ts` (112 lines, 8 assertions) pins missing-var detection; `builder.test.ts` (493 lines, 15 assertions) pins placeholder/env/header outcomes. Runner absent in checkout — pinned by direct test reads of both files' describe blocks.
**Coverage:** builder.ts, env.ts, validator.ts all `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "buildUrlAndHeadersForRegistryItem name style placeholder", limit: 10 });
```

## Verdict
Adopt the full ladder: builtin-under-user merge, fail-loud unknown namespace, pre-flight env validation, ordered placeholder→env→params substitution, and unexpanded-header suppression (the subtlest contract here). Adapt placeholder vocabulary and error copy to your domain. Omit v0's `/chat/b/` `/json` suffix special-case in `resolveRegistryUrl` unless you serve that API.
