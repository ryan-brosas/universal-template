<!-- capsule-v2 -->
# Declarative route-anchor rule pack — how do five framework port shapes become data instead of code?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Route extraction across express/gin/NestJS/Go-1.22/chi/Django/Rails/Phoenix/Ktor/Spring/Next/SvelteKit — how do you add frameworks without writing extractors, and what validates a captured token as a real route?

## Rule pack + path-token discriminator + class prefixes
**Path/Symbol:** `src/core/anchors.ts:AnchorRule/DEFAULT_PACK/extractAnchors/FileRouteRule/extractFileRoutes/loadRepoRules/compileMethods` (:27-477); repo rules at `.fovea/rules.json`.
**Signature:** `extractAnchors(files, cwd, resolveEnclosing, pack): Promise<AnchorDraft[]>`; `compileMethods(methods: string): RegExp` rewrites ES2025 inline `^(?i:get|post)$` to a trailing-flag group (issue #1: Node < 23 cannot parse the modifier form).
**Data Shape:** Rule = `{id, langs[], pattern?|patterns?, methods regex, kind, prefixPattern?, verbFrom?, mountRoot?, implicit?}`. Metavars: `$P` path arg (an arg NODE — quote chars incl. Python f-string prefixes stripped by `unquote`), `$M` method, `$R` receiver, `$V` verb metavar, `$$$H` trailing hole.

### Decisive source
```ts
// Every captured token still has to validate as a path before it can become a
// hub — the route string is the real discriminator, the call shape is flavor.
if (!PATH_TOKEN_RE.test(raw) && !PLACEHOLDER_ONLY.test(raw)) continue;
// $R.$M(...) also matches Map.get("key")-style data access; only real paths
// (or router-relative placeholders like ":id", "[id]") anchor.
```
```ts
// Class-level prefix composition (NestJS @Controller('api/x') + @Get('y')):
const prefixes = new Map<string, string>();   // file -> prefix, via patternRunAll on prefixPattern
let raw = prefix !== undefined && prefix !== "" ? joinRoute(prefix, unquote(pathLike)) : unquote(pathLike);
// Verb-in-path (Go 1.22 mux.HandleFunc("GET /x", h)):
const vip = VERB_IN_PATH.exec(raw);
if (vip) { verbOverride = vip[1]!.toUpperCase(); raw = vip[2]!; }
// Mount-not-verb methods (Django path/re_path/url, Rails match/root, Spring @RequestMapping):
const METHOD_ALIASES = { PATH:"ANY", RE_PATH:"ANY", URL:"ANY", MATCH:"ANY", REQUESTMAPPING:"ANY", FETCH:"GET", REDIRECT:"GET", ... };
```

**Flow:** per rule × language → optional prefix pass (`prefixPattern`, first capture per file wins) → patternRunAll matches → method-regex check → unquote → compose prefix → mountRoot rooting → verb-in-path split → PATH validation → deriveVerb / verbFrom (must be a real HTTP verb else reject) → `normalizeLiteral(·,"path")` placeholder canonicalization → anchor id `"<VERB> <path>"` bound to enclosing symbol (else `file:<path>`) → site dedupe by `id|file|line`. File-convention routers run separately: filename regexes + exported-handler verbs or `.get` suffix verbs; dynamic segments `[x]/[...x]/[[...x]]` → `{*}`; `(group)` segments vanish; zero verbs → `ANY`.
**Invariant:** The call shape is flavor, the validated path string is the discriminator — Map.get-style false positives die here. Cache invalidation is hash-driven: `DEFAULTS_SHA = sha1(JSON(DEFAULT_PACK)+JSON(DEFAULT_FILE_ROUTES))` and repo rules hash `DEFAULTS_SHA + raw`, so upgrading pi-fovea invalidates anchors even with no repo rules file. Repo rules EXTEND defaults; malformed entries are filtered, not fatal.
**Probe:** `tests/extract.test.ts` — "covers ecosystem route shapes" (mux GET /healthz, chi, Spring prefix, Django ANY, Rails both quote styles, Phoenix scope NOT composed, Ktor lambda, template/f-string client calls, Django legacy regex must NOT anchor); "derives anchors from file-convention routers"; "normalizes variable items whose name inlined a huge C initializer"; compileMethods regression suite + pre-modifier engine simulation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "extractAnchors AnchorRule prefixPattern", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the declarative pack (rules as data), the $P-as-node any-quote capture, path-token final validation, class-prefix composition, verb-in-path and ANY-mount semantics, file-route derivation, and the double-hash cache invalidation. Adapt the pack contents to your target frameworks. Omit documented blind spots as features-to-port-later: Rust proc-macro attrs, constructor-assigned prefixes (Blueprint/APIRouter/Mount), scope nesting, tRPC/gRPC (no path token).
