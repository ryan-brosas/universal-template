<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# shadcn/ui: Registry Client Plane Foundation

## Use this for
Use when porting multi-registry content-fetching clients: private/authenticated
component or asset registries, `@namespace/item` addressing, dependency-tree
resolution before install, proxy/corporate-network fetch layers, or CLI error
reporting with actionable suggestions. Source code and direct tests are ground
truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./registry-error-taxonomy.md` — how do I map HTTP failures to typed, actionable errors without losing the server's own message?
- `./fetch-promise-cache.md` — how do I dedupe concurrent identical fetches without a request-library cache?
- `./registry-context-als.md` — how do per-invocation auth headers reach deep async fetches without threading parameters?
- `./namespaced-url-builder.md` — how does `@acme/button` become a real URL + headers from user config?
- `./item-address-scheme-dispatch.md` — given any item string, which transport owns it?
- `./resolve-tree-dependency-walk.md` — how does one `add` resolve an entire transitive registry-dependency tree into one installable bundle?
- `./topological-source-hash-sort.md` — how are resolved items ordered so dependencies install first, even with same-named items from different sources?
- `./proxy-fetch-origin-redirects.md` — how do custom secret headers survive redirects and proxies safely?
- `./github-anonymous-lock-auth-ladder.md` — when may a GitHub source client ever send credentials, and what stops a public source from ever authenticating?
- `./github-transport-error-sanitation.md` — how do REST+subprocess failures become actionable errors without leaking tokens or raw output?
- `./gh-subprocess-hermetic-env-slot.md` — how do you bound a `gh` subprocess fleet and force it onto its own stored credential?
- `./streaming-oversize-read-cap.md` — where must a file-size ceiling bite so hostile payloads never land in memory?
- `./github-ref-resolution-ladder.md` — how does `owner/repo#v1.2.0` become a pinned SHA in one network call (and what if git is missing)?
- `./rejection-evicting-source-cache.md` — when must a promise cache delete failed entries instead of retaining them?
- `./bounded-concurrency-validation-sweep.md` — how do you validate every catalog item under a concurrency cap while attributing failures to their registry file?

## Capsule map
- **Registry error taxonomy** — `registry-error-taxonomy`: status→subclass mapping (401/403/404/410) plus RFC 7807 `detail` > `message` > `[error]` extraction feeding every error's suggestion field.
- **Fetch promise cache** — `fetch-promise-cache`: `Map<string, Promise<T>>` stores the in-flight promise BEFORE awaiting; key = `url:sha256(lowercased+sorted headers)`; failed promises stay cached until `clearRegistryCache()`.
- **Registry ALS context** — `registry-context-als`: AsyncLocalStorage store of `{headers: url→headers, env, onGitHubAuthNotice}`; nested `setRegistryHeaders` merges so dependency resolution keeps outer headers.
- **Namespaced URL builder** — `namespaced-url-builder`: `{name}`→item, `{style}`→config.style (only if placeholder present), `${VAR}` expansion to `""` when unset; var-bearing headers whose expansion is a no-op are dropped; missing vars pre-flight as `RegistryMissingEnvironmentVariablesError`.
- **Item address dispatch** — `item-address-scheme-dispatch`: order url → file (`.json` && !url wins over GitHub!) → namespace → github `owner/repo/item[#ref]` → shadcn default; refs reject whitespace/control-chars/leading-dash.
- **Dependency tree walk** — `resolve-tree-dependency-walk`: `_source` tracking, fail-loud `@ns` deps without config, deferred non-namespaced deps via index phase, theme injection only for `index`, last-wins file dedupe by target path, deliberate NO name-dedup.
- **Topological source-hash sort** — `topological-source-hash-sort`: node id = `` `${name}::${sha256(source||name).slice(0,8)}` ``; Kahn's algorithm; cycles tolerated by appending leftover items unsorted.
- **Proxy fetch + origin-scoped redirects** — `proxy-fetch-origin-redirects`: manual redirect loop ≤5; cross-origin hop resets caller headers to `{accept,user-agent}` because native fetch preserves custom names like `X-API-Key`; undici `EnvHttpProxyAgent` / SOCKS via `ALL_PROXY`.

### GitHub content-source & transport plane (pass 2)
- **Anonymous-lock auth ladder** — `github-anonymous-lock-auth-ladder`: anonymous raw read first; ONLY the initial root `registry.json` 404 may select token-vs-gh (single-flight decision promise with rollback, process-wide notice dedup); a public root sets `anonymousLock` so child 404s never authenticate; credentials reach only api.github.com.
- **Transport error sanitation** — `github-transport-error-sanitation`: errors carry only sanitized `kind`+range-checked `statusCode`; stderr regex-classified then discarded; guidance from a fixed-string table keyed by kind×mode; tokens gated by printable-ASCII `/^[\x21-\x7E]+$/` before any header.
- **gh hermetic-env slot semaphore** — `gh-subprocess-hermetic-env-slot`: 8-slot counting semaphore with direct finisher→waiter slot handoff; `extendEnv:false` env rebuild deletes all credential/debug vars and pins `GH_HOST=github.com`, prompt/pager/telemetry off.
- **Streaming oversize read cap** — `streaming-oversize-read-cap`: Content-Length pre-check → streamed cumulative byte counter with `reader.cancel()` on breach → buffered post-check for gh stdout; one 5 MiB constant across all three tiers; sha re-validated before URL interpolation.
- **Ref resolution ladder** — `github-ref-resolution-ladder`: 40-hex SHA fast-path (zero subprocess); ONE `git ls-remote --symref` call with branch > peeled-tag (`^{}`) > tag-object preference, `GIT_TERMINAL_PROMPT=0` + 15s timeout; authenticated REST fallback mirrors the same order (branch first, tag only on 404, tag-peel depth ≤5).
- **Rejection-evicting source cache** — `rejection-evicting-source-cache`: per-invocation source caches store promises BEFORE awaiting but evict rejections via an identity-guarded `.catch` — deliberate contrast to the retain-until-clear registry fetch cache.
- **Bounded-concurrency validation sweep** — `bounded-concurrency-validation-sweep`: shared-cursor worker pool (8 fibers, order-preserving results) validates each catalog item; a readText-decorating tracking reader records every traversed registry.json; failures flatten into diagnostics from `RegistryError.context`.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed
porting question. Add one matching loader line and map entry; keep evidence in
the capsule, not this leaf.

## Provenance
shadcn-ui (UNLICENSED — all-rights-reserved default; reuse citations-only),
`main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory project
`shadcn-ui` (full mode, generation 2026-08-25T20:00:37Z, 36183n/119404e;
137 parse-partial files confined to apps/v4 examples/blocks/CSS and
commands/{eject,preset,search} test files — none cited here). Pass 1 mined the
registry client plane core; pass 2 (same pin, zero drift) added the GitHub
content-source & transport plane with 7 more capsule-v2.

## Full view (memory graph)
Revalidate `shadcn-ui` before porting: run `index_status`,
`check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`.
Record the graph root, branch, commit, mode, node/edge counts, freshness, and
any coverage caveats; source and direct tests decide shipped claims. The plane
lives under `packages/shadcn/src/registry/*`; `trace_path(function_name:
"getRegistryWithContext")` is the fastest whole-neighborhood entry and
`trace_path(function_name: "fetchGitHubRegistryItem")` opens the GitHub source
plane (22 callees / 19 callers).

## Boundaries
Adopt pure contracts: error taxonomy shape, promise-cache mechanics, address
dispatch ordering, placeholder/env templating, origin-scoped redirect policy,
topological sort with cycle tolerance, GitHub auth-ladder/sanitation/ref/
cache/concurrency contracts. Adapt host-specific integration:
AsyncLocalStorage (Node-only), undici dispatcher option, zod schemas, MSW-based
test seams, execa subprocess transport. Omit product behavior: shadcn-specific
builtin registries/styles, v0 `/chat/b/` URL special-casing, docs-site app,
template generators, GitHub-host-specific URL constants where a generic host
parameter suffices.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`bounded-concurrency-validation-sweep.md`](./bounded-concurrency-validation-sweep.md)
- [`fetch-promise-cache.md`](./fetch-promise-cache.md)
- [`gh-subprocess-hermetic-env-slot.md`](./gh-subprocess-hermetic-env-slot.md)
- [`github-anonymous-lock-auth-ladder.md`](./github-anonymous-lock-auth-ladder.md)
- [`github-ref-resolution-ladder.md`](./github-ref-resolution-ladder.md)
- [`github-transport-error-sanitation.md`](./github-transport-error-sanitation.md)
- [`item-address-scheme-dispatch.md`](./item-address-scheme-dispatch.md)
- [`namespaced-url-builder.md`](./namespaced-url-builder.md)
- [`proxy-fetch-origin-redirects.md`](./proxy-fetch-origin-redirects.md)
- [`registry-context-als.md`](./registry-context-als.md)
- [`registry-error-taxonomy.md`](./registry-error-taxonomy.md)
- [`rejection-evicting-source-cache.md`](./rejection-evicting-source-cache.md)
- [`resolve-tree-dependency-walk.md`](./resolve-tree-dependency-walk.md)
- [`streaming-oversize-read-cap.md`](./streaming-oversize-read-cap.md)
- [`topological-source-hash-sort.md`](./topological-source-hash-sort.md)
