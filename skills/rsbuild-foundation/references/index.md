<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Rsbuild: bundler-framework kernel foundation

## Use this for
Use when porting build-tool/dev-server architecture: plugin registries with ordering constraints, lifecycle hook engines, multi-environment config merging, WebSocket HMR protocols, dev-server middleware stacks with HTTP-caching semantics, or restarting process supervisors. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./instance-assembly.md` — how does `createRsbuild` assemble an immutable-ish instance whose actions share one lazily-created compiler?
- `./plugin-ordering.md` — how are plugins validated, ordered (before/enforce/pre/post) and removed without breaking env scoping?
- `./async-hook-engine.md` — how do the tap/callChain/callBatch hook primitives thread results and filter by environment?
- `./compiler-hooks-bridge.md` — how do rsbuild hooks map onto Rspack run/watchRun/done across a MultiCompiler?
- `./plugin-api-surface.md` — how does `api.transform`/`processAssets`/`expose` reach into Rspack compilations per environment?
- `./config-merge-semantics.md` — which keys override instead of merge, and how do functions become chains?
- `./config-init-pipeline.md` — what is the exact order from user config to normalized per-env configs to Rspack configs?
- `./context-model.md` — what is exposed on `context`, why is it Proxy-guarded, and where does the HMR token come from?
- `./env-loading.md` — how are .env files parsed, expanded, prefixed into define vars and cleaned up?
- `./dev-server-lifecycle.md` — how does the dev server resolve ports, defer compilation, close exactly once and keep restart watchers alive?
- `./compile-state-env-api.md` — how do callers wait for per-environment stats and cache bundles keyed off stats identity?
- `./hot-path-projection-caches.md` — how does the SSR/HTML request path avoid re-deriving per-entry data without leaking compilations?
- `./dynamic-port-restart-handoff.md` — how does `server.port: 0` keep the SAME port across restarts via an options-object WeakMap handoff?
- `./startup-failure-rollback.md` — how do dev/preview servers release the port and run close hooks when startup throws?
- `./socket-server-hmr.md` — what decides ok/hash/errors/warnings/full-reload messages per connected token?
- `./hmr-client.md` — how does the browser client apply updates, fall back to reload, reconnect, and report runtime errors?
- `./assets-middleware.md` — how are dev assets served safely from memory with correct conditional-GET and range behavior?
- `./middleware-stack.md` — what is the exact middleware ordering and how do gzip/proxy interact with it?
- `./restart-shutdown.md` — how do restart requests run cleanups exactly-once and keep watchers alive for retry?
- `./file-size-report.md` — how are cross-build size diffs computed from hash-stripped snapshot files?
- `./html-pipeline.md` — how do tags flow through html plugin hooks, inlining, crossorigin/nonce post-passes?
- `./ssr-bundle-runner.md` — how are emitted bundles executed in Node with CJS/ESM requirers over vm?
- `./css-import-loaders-counter.md` — why do inline/url branches count one more preceding loader than main?
- `./css-postcssrc-cache-wrapper.md` — why is postcssrc cached per root (promise-first) and function options wrapped twice?
- `./css-url-loader-pitch.md` — why does the ?url loader re-execute the css pipeline via importModule and emit with immutable?
- `./ignore-css-pitch-gate.md` — why does the non-emitting SSR build keep css-loader ONLY for CSS Modules?
- `./minify-removeconsole-purefuncs.md` — why does drop-console use compress.pure_funcs and never delete calls?
- `./externals-auto-rules.md` — why are deps compiled to `^pkg(?:$|[\\/\\])` regexes and dropped on workers?
- `./swc-script-rule-assembly.md` — why do include conditions accumulate additively and env get deleted when jsc.target appears?
- `./resolve-dedupe-alias.md` — why does dedupe walk up node_modules and alias only absolutize dotted relatives?
- `./split-chunks-dispatcher.md` — why does per-package name() win at negative priority and MF flip chunks to async?
- `./cache-build-dependencies.md` — why must framework/tsconfig/tailwind configs be listed as buildDependencies explicitly?
- `./lazy-compilation-server-url.md` — why does a relative assetPrefix mean "follow page origin" and single-entry skip entries?
- `./entry-registration-guard.md` — why does core-js become a VIRTUAL pre-entry and MF apps get an empty entry?
- `./target-browserslist-short-circuit.md` — why does the default browserslist compile to es2017 and web-worker lose browserslist?
- `./output-publicpath-ladder.md` — why does dev default to a <port> placeholder and 0.0.0.0 rewrite to localhost?
- `./sourceMap-extract-ladder.md` — why does prod js default sourceMap FALSE and legacy extract.js survive one more major?
- `./clean-dist-gates.md` — why is cleanDistPath 'auto' a strict-subdir test plus writeToDisk check?
- `./asset-query-ladder.md` — why do ?url/?inline/?raw/type:text outrank the size-gated default asset branch?
- `./inline-chunk-mark-sweep.md` — why is inline deletion a summarize-stage pass over a recorded set?
- `./manifest-entry-partition.md` — why do initial files come from entrypoints and async from the chunk walk?
- `./resource-hints-links.md` — why are preload/prefetch hints injected into assetTags.styles and deduped against script srcs?
- `./app-icon-pwa-plane.md` — why do appIcon errors go to the compilation instead of throwing?
- `./sri-nonce-security.md` — why does SRI force crossOriginLoading and nonce inject via anonymous EntryPlugin?
- `./define-env-leak-guard.md` — why does the define leak guard JSON.parse stringified values and compare live process.env?
- `./html-fallback-ladder.md` — why do completion/fallback middlewares re-invoke the assets middleware instead of serving files?
- `./history-fallback-rewrite-ladder.md` — why does the dot-rule compare lastIndexOf positions and JSON clients get skipped?
- `./browser-logs-symbolication.md` — why is only the first user frame mapped and when do runtime frames survive?
- `./stats-error-formatter.md` — why does the file line end with :1:1 and traces reverse to entry→error?
- `./compiler-lifecycle-taps.md` — why does watchRun own the "building" log and done() own the time print?
- `./build-manager-shutdown.md` — why does close() order socket→middleware→compiler and refcount signal handlers?
- `./cli-shortcuts-readline.md` — why is the shortcut registry rebuilt through a user callback that may throw?
- `./watch-files-groups.md` — why do dev watchFiles and server publicDir get separate watcher lifecycles?
- `./server-public-dir-copy.md` — why does copyOnBuild 'auto' skip node targets at first compile only?
- `./config-loading-contract.md` — why does the config fn receive {env, command, envMode, meta} and get _privateMeta stamped?
- `./default-config-skeleton.md` — why are defaults FACTORY functions and assetPrefix a deferred placeholder?
- `./path-fs-kernels.md` — why does dedupeNestedPaths sort by LENGTH and isEmptyDir treat .git-only as empty?
- `./e2e-harness-fixtures.md` — why does copySrcDir exist and devOnly/buildPreview split the server lifecycle?
- `./create-toolkit-template-wiring.md` — how does the CLI bind framework templates, aliases, and optional tools/skills onto the external `create()` kernel?
- `./octane-template-plane.md` — what does a first-class third-party-framework template require beyond a config file, and why does `.tsrx` exist?
- `./config-text-rewrite-kernel.md` — how do you add plugins to a generated `rsbuild.config` file textually, idempotently, and in deterministic order?
- `./react-compiler-config-surgery.md` — how is `pluginReact()` upgraded to `pluginReact({ reactCompiler: true })` in place, and what happens on a second run?
- `./tailwind-tool-action.md` — how does a scaffolder inject BOTH a config plugin and a CSS import, and why does it probe two filenames?
- `./create-e2e-harness.md` — how do you behaviorally test a scaffolder CLI without installing anything?
- `./template-corpus-conventions.md` — what must every framework template directory contain, and which per-framework deltas are contractual?
- `./transform-pipeline-loaders.md` — how does `api.transform` reach module content without one loader per transform, and when do source maps survive?
- `./worker-loader-inline-child-compiler.md` — how do `?worker` imports become URL wrappers, and why must inline workers be single-file?
- `./node-addons-transform.md` — how are `.node` binaries shipped and re-required at runtime without bundler interference?
- `./wasm-url-dependency-rule.md` — why does the `.wasm` rule scope to `new URL` dependencies, and what does `webassemblyModuleFilename` own?
- `./env-gated-diagnostic-plugins.md` — how do progress, Rsdoctor, and Rspack profiling opt in without config surface?
- `./browser-error-overlay-plane.md` — how do server-formatted errors become a dismissible shadow-DOM overlay, and why does hostname resolution probe DNS twice?
- `./html-plugin-implementation-singleton.md` — how does one selector choose native vs vendored-JS html-plugin, and why does the require go through a compiled folder?

## Capsule map
- **Instance** — `instance-assembly`: one shared lazy compiler promise behind dev/build/preview actions; action type frozen on first use.
- **Plugins** — `plugin-ordering`: meta-store {instance, environment}; validate → before-insert → enforce groups → topological pre/post sort with loud cycle error → `remove` resolution before any setup runs.
- **Hooks** — `async-hook-engine`: pre/default/post arrays; `callChain` threads first param when defined, `callBatch` collects results; env hooks run global taps plus same-env taps.
- **Compiler bridge** — `compiler-hooks-bridge`: one `beforeCompile` latch per invalidation shared by all sub-compilers; done-count with per-compiler flags decremented on invalid composes MultiStats. `compiler-lifecycle-taps`: run/watchRun/invalid/done tap matrix — watchRun owns the "building" log, done() owns the time print; lazy-module infrastructureLog mining; MultiCompiler prints per-child then aggregate.
- **Plugin API** — `plugin-api-surface`: closures per environment; transform handlers ride a symbol-keyed map on the compiler to a generic loader; processAssets descriptors filtered by target/env at tap time.
- **Config** — `config-merge-semantics`: dot-path override list, array concat, function chaining, boolean beats object, deep-clone isolation. `config-init-pipeline`: plugins → modifyRsbuildConfig (warn-only plugin mutation) → normalize → per-env base merge + node defaults → modifyEnvironmentConfig → sequential deterministic Rspack config generation.
- **Context** — `context-model`: internal context + read-only public proxies; dev-only `webSocketToken` = sha256(rootPath+envName)[0:16].
- **Env** — `env-loading`: `.env`, `.env.local`, `.env.[mode]`, `.env.[mode].local`; NODE_ENV survives expansion and cleanup; empty prefix throws (would inline every var).
- **Server** — `dev-server-lifecycle`: net-probe port ladder with strictPort, runCompile:false stubs, memoized close resources, restart watcher outlives failed restarts. `dynamic-port-restart-handoff`: port-0 captured inside the probe; options-object WeakMap stash lives only for the restart() call; strictPort suppressed while inheriting; `<port>` client sentinel substituted at middleware setup. `startup-failure-rollback`: awaitable once(server,'listening'); rollback rides the production close path; original error beats close errors; terminator destroys sockets before close with never-listened guard. `compile-state-env-api`: deferred-per-env stat waits reset on watchRun; WeakMap(stats)-keyed bundle caches drop failures. `hot-path-projection-caches`: stats projection WeakMap per compilation + lazily-materialized outputFilePaths Set + single-flight promise cache with self-evicting failures. `socket-server-hmr`: token-authenticated sockets; initial-chunk-set changes force full-reload; hash-unchanged clean builds short-circuit to `ok`. `hmr-client`: BUILD_HASH sentinel, idle-gated hot.check(true), 1.5^n backoff, queued client errors, searchParams prototype probe before URL-API use.
- **HTTP** — `assets-middleware`: memfs output FS, ready-queue until status==='done', traversal/null-byte guards, public-prefix-first resolution, ETag/freshness/single-range ladder. `middleware-stack`: fixed ordering with user unshift/push slots; gzip wraps write/writeHead/end handling raw header arrays and skipping SSE; proxy bypass verbs false/string/true.
- **Lifecycle** — `restart-shutdown`: cleanup-set swap on requestRestart (all cleanups run even if one throws; registry cleared so retry doesn't re-run); SIGINT only exits if it is the sole listener; SIGTERM+128 POSIX code. `watchFilesForRestart` groups chokidar watchers, ignores initial adds and permission errors.
- **Reporting** — `file-size-report`: per-config-file hashed snapshot JSON, hash-stripped asset names, ≥10-byte diffs, gzip only for non-node targets and compressible extensions. Error formatting (`formatStatsError`) resolves moduleIdentifier loader chains, truncates import traces to head/tail, and rewrites missing-loader hints into plugin recommendations.
- **HTML** — `html-pipeline`: template params reduce per entry; title injected only if template lacks one; favicon emitted once via existence check; tag priority sort (head ±2, append ±1); inline-chunk rewrites tags at modifyHTMLTags and deletes assets at summarize stage preserving source maps via `related.sourceMap: null`.
- **SSR** — `ssr-bundle-runner`: entry chunk must be unique and non-CSS; CJS via `vm.compileFunction` with require cache; ESM via `SourceTextModule` with `--experimental-vm-modules` gate and SyntheticModule bridging.
- **CSS plane (pass 2)** — `css-import-loaders-counter`: twin {normal,inline} counters; inline/url branches see +1 per pre-loader that only they host; inline/url force `exportType:'string' + modules:false`. `css-postcssrc-cache-wrapper`: promise-then-value per-root cache, clone-on-read, concat-not-overwrite plugin merge, eager creator invocation (#3618), `config:false` on wrapper. `css-url-loader-pitch`: pitch-phase `importModule('!!'+req)` child build, src-relative naming ladder, compilation-hash reuse, hash-placeholder ⇒ immutable, runtime publicPath concat. `ignore-css-pitch-gate`: pitch '' skips global CSS entirely while CSS Modules fall through for SSR exportOnlyLocals; normal phase strips `___CSS_LOADER_EXPORT___` sentinel.
- **Transform/minify plane** — `minify-removeconsole-purefuncs`: prod-gated tri-state with 'always' escape; removeConsole → pure_funcs `console.*`; css minimizer inherits loader options; array options multiply minimizer ids, empty array still registers default. `swc-script-rule-assembly`: additive includes (node_modules-not + TS/JSX always + dev runtime), decorator version switch w/ useDefineForClassFields:false legacy quirk, jsc.target/env exclusivity delete, cloneDeep for data-URI twin rule, core-js version sniff + alias.
- **Resolve/entry/target plane** — `resolve-dedupe-alias`: root-resolved dedupe with pnpm walk-up to node_modules/<pkg>, alias-wins precedence, dot-relatives-only absolutization, tsconfig extensionAlias, mjs fullySpecified:false. `entry-registration-guard`: order preEntry→virtual core-js→user; html-key strip; MF constructor-name detection sets entry={} post-order else loud throw. `target-browserslist-short-circuit`: joined-string default test → bare es2017 vs browserslist: query; worker degrades es5 (upstream TODO). `externals-auto-rules`: autoExternal dependency lists compile to anchored `^pkg(?:$|[/\])` RegExp rules with exclusion ladder; worker environments wipe the rule set.
- **Chunk/output plane** — `split-chunks-dispatcher`: six-strategy dispatcher; enforced force-groups beat single-vendor at priority 1; per-package name() at priority −9 with pnpm-guarded regex; server splits by default (chunks:'all', preset 'none' escape), worker default-off; MF provider apps chunks:'async'. `output-publicpath-ladder`: prod assetPrefix / dev true→live-context synthesis with <port> placeholder replaced AFTER base join; 0.0.0.0→localhost; web const:false TDZ dodge; ESM chunkFormat/module loading flip; server commonjs2/module library.
- **Caching/lazy plane** — `cache-build-dependencies`: package.json/tsconfig/rsbuild config+deps/browserslistrc/tailwind explicit list; version `${env}-${NODE_ENV}[-digestHash]`; persistent filesystem storage under cachePath/rspack; missing files silently skipped. `lazy-compilation-server-url`: relative assetPrefix ⇒ same-origin endpoint (return undefined); absolute/client-host derive URL; single-entry ⇒ entries:false; object serverUrl gets live <port> rewrite.
- **Asset pipeline** — `asset-query-ladder`: oneOf order url→inline→text→raw→size-gated default; emit-off rides generator.merge not rule removal; exts regex non-capturing only when plural. `inline-chunk-mark-sweep`: modifyHTMLTags rewrites tags + records names in per-env Set; summarize-stage deleteAsset AFTER html plugin read bytes; related.sourceMap:null rescues maps; lazy Rust-JS bridge access behind regex-first tests. `manifest-entry-partition`: initial from entrypoint.getFiles() (CSS order), async from !isInitial walk; LICENSE.txt reassociation via split-map; integrity passthrough; cross-env duplicate-filename warning latch. `resource-hints-links`: multi-HTML scoping via recursiveChunkEntryNames visited-set; unconditional .map/.hot-update exclusion; include-OR/exclude-OR algebra; sort before emit; font preload crossorigin:''; links prepend into styles array deduped by rel:href against script srcs. `app-icon-pwa-plane`: cache-keyed formatIcon, inputFileSystem existence checks, addCompilationError isolation per icon, manifest.webmanifest assembly.
- **Security/config plane** — `sri-nonce-security`: auto=prod; SRI forces crossOriginLoading anonymous; nonce dual-path (nameless EntryPlugin virtual module sets import.meta.rspackNonce + post-order tag stamping incl. preload as=script). `define-env-leak-guard`: builtin import.meta.env MODE/DEV/PROD/SSR/BASE_URL/ASSET_PREFIX; whole-env leak probe detects both object and JSON-stringified forms via case-insensitive PATH equality. `sourceMap-extract-ladder`: true→prod 'source-map'/dev cheap-module; object-form js undefined ⇒ prod FALSE; extract.js:false always wins; two rule names for legacy/flat shapes. `clean-dist-gates`: strict-subdir (trailing-sep) + dev writeToDisk suppression; keep regexes posix-tested and guard rmdir; fail-open cleanup. `config-loading-contract`: 6-name ladder ts-first; fn receives {env,command:argv[2],envMode,meta}; fresh:true bypasses require cache; _privateMeta stamps filePath+dependencies for restart/cache. `default-config-skeleton`: factory-per-env defaults (never hoisted); loopback-only CORS regex incl. *.localhost; decorators default '2023-11'; client reconnect 100.
- **Server extras** — `html-fallback-ladder`: maybeHTMLRequest = GET/HEAD + text/html-or-*/* accept; completion '/'→index.html & extensionless→.html gated on outputFileSystem existence then DIRECT assetsMiddleware invocation; base middleware strips prefix / 302-root-with-query / styled-vs-plain 404 split. `history-fallback-rewrite-ladder`: method→accept(json-prefix skip)→explicit rewrites→dot-rule lastIndexOf comparison→index; x-forwarded-aware URL parse; parse failure never throws. `browser-logs-symbolication`: summary tier maps ONLY findFirstUserFrame via per-connection CachedTraceMap; sources joined relative to MAP dir then root-relativized; runtime frames filtered only when a located non-runtime frame survives; process-undefined hint block. `build-manager-shutdown`: close order socket→middleware→compiler; outputFileSystem late-bound with readFileSync fallback to node:fs; cleanup Set + refcounted SIGTERM(+128)/stdin-end install; preview close-once promise memo. `cli-shortcuts-readline`: TTY-gated install; trim().toLowerCase() dispatch (unit-pinned); immutable 'h' help handler; q exits in finally after closeServer. `watch-files-groups`: hmr/liveReload gate BEFORE watchers; per-group chokidar instances; publicDir opt-in watch; aggregate Promise.all close. `server-public-dir-copy`: isFirstCompile gate inside build hook; copyOnBuild 'auto' filters node targets; nested-dedupe destinations; tinyglobby ignore→copy filter.
- **Reporting kernels** — `stats-error-formatter`: file||moduleName||last-!-segment resolution; clickable :1:1 default; trace reversed entry-first then HEAD/TAIL=2 truncation MAX 4; ordered hint chain (loader→node-polyfill→assets-conflict); inner-error strip when not verbose; child-stats error fallback. `path-fs-kernels`: dedupeNestedPaths length-sort + startsWith reduce; getCommonParentPath segment-wise; isEmptyDir '.git'-only counts empty; normalizeRuleConditionPath windows absolute-slash conversion; emptyDir keep-regex posix tests guard rmdir.
- **Test harness** — `e2e-harness-fixtures`: copySrcDir fixture isolation; devOnly/buildPreview/build lifecycle splits; buffered expectLog/clearLogs phase separation; in-memory dist file map assertions.
- **Scaffolder plane (pass 4)** — `create-toolkit-template-wiring`: three-way identity contract (CLI `-t` value ≡ prompt value ≡ `template-<name>` dir/`templates:` array entry), `split('-')` + `?? 'js'` grammar, alias-normalize-before-lookup (`vue3`→vue, `solid-js`→solid), extraTools action/command duality with `isMergePackageJson`. `octane-template-plane`: extension+syntax+owner-plugin travel as one unit (`.tsrx`, `@{ }` bodies, `pluginOctane()`); pnpm `allowBuilds: esbuild: true` is load-bearing for install. `config-text-rewrite-kernel`: base-snapshot regeneration + id-keyed plugin Map + `(order ?? 0)` sort = idempotent deterministic textual config edits; single-line vs multi-line array duality keyed on ends-with-`],`; empty-config seed replacement; last-import splice anchor. `react-compiler-config-surgery`: exact-token `pluginReact()` → `pluginReact({ reactCompiler: true })` upgrade with two-shape match grammar and the proven double-write hazard when a mutation bypasses the cache. `tailwind-tool-action`: first-existing-file prepend-and-break CSS injection + order-tagged plugin descriptor (`order: 20`). `create-e2e-harness`: exec-real-binary + inspect-artifacts testing with universal-manifest invariants, per-suite deltas, CRLF normalization, and exact-string config snapshots as formatting contract. `template-corpus-conventions`: 21-dir minimum-skeleton rule, `{{ packageManager }}` placeholder grammar in AGENTS.md templates, and the contractual per-framework deltas (lit html+legacy-decorators, solid2 babel twin, svelte browserslist, react-ts env.d.ts, octane allowBuilds+.tsrx).

- **Transform surface (pass 5)** — `transform-pipeline-loaders`: ONE generic loader pair (`transformLoader.mjs` + raw twin `export const raw = true`) resolves handlers from symbol-keyed `compiler.__rsbuildTransformer[id]` at transform time; no-op fallbacks for missing id/transform/null result; source maps merged via remapping only when BOTH sides exist, string/Buffer results keep the incoming map.
- **Native/worker plane (pass 5)** — `worker-loader-inline-child-compiler`: `[?&]worker` oneOf rule → URL-wrapper module (basename-only request) or inline child-compiler build with `dynamicImportMode:'eager'`, loud code-splitting rejection, parent-side asset+map deletion, dep propagation, self-revoking blob wrapper w/ data-URL fallback. `node-addons-transform`: `.node` rides the RAW transform on node targets only; emit + runtime re-require (`createRequire` ESM / `__non_webpack_require__` CJS) with cause-preserving load errors; web/web-worker get no rule (snapshot-pinned). `wasm-url-dependency-rule`: `webassemblyModuleFilename` owns intrinsic wasm output while the `.dependency('url')`-scoped asset/resource rule claims ONLY `new URL(...)` wasm — both share the dist path template.
- **Diagnostics plane (pass 5)** — `env-gated-diagnostic-plugins`: progress = computed env-name prefix is only a default (user options spread AFTER), rsdoctor = `RSDOCTOR=true` checked at onBeforeCreateCompiler, mutates GENERATED bundlerConfigs, dedupes across all envs by `isRsdoctorPlugin||constructor.name`, fail-soft optional peer resolved from rootPath (+Windows file-URL import); rspackProfile = `RSPACK_PROFILE` presets OVERVIEW→info / ALL→trace / raw EnvFilter, perfetto forbids stdout/stderr, default `.rspack-profile-<ts>-<pid>/` dir, register once per build/dev start, fire-and-forget `globalTrace.cleanup()` on exit.
- **Browser error overlay (pass 5)** — `browser-error-overlay-plane`: server pipeline ORDER IS THE CONTRACT (escapeHtml → ansiHTML → convertLinksInHtml) with node:internal/webpack-runtime skip-lists, ANSI close-span relocation, data-file absolutization vs pretty display text, pnpm last-segment collapse; socket message carries complete `text` + overlay-filtered `html`; client custom element `<rsbuild-error-overlay>` shadow-DOM w/ one-shot Esc listener, immediate-close dedup, open-in-editor fetch, warn-fallbacks; `resolveHostname` double DNS lookup guard feeds applyHMREntry (misleading filename: NOT a websocket fallback).
- **HTML impl selector (pass 5)** — `html-plugin-implementation-singleton`: `getHTMLPlugin` flips native `rspack.HtmlRspackPlugin` vs vendored-JS `compiled/html-rspack-plugin` on `html.implementation`; memoizes ONLY the JS path in module scope; CJS-vendored deps require a `createRequire(import.meta.url)` bridge.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
rsbuild (MIT), pin advanced pass 4 to `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5` (pass 3 `bc19fd5e`, passes 1-2 `ded92636…`); Codebase Memory project `mnt-hdd-utopia-inspo-frameworks-rsbuild` — path-slugged TWIN adopted 2026-08-24 (in-place re-index registered the twin while short-name `rsbuild` kept serving pre-drift spans; resolvePort 453–473 stale vs 498–520 at HEAD; pass 4 re-indexed the twin IN PLACE at 2bcf61c: 14,580 nodes / 27,023 edges, generation 2026-08-24T07:26:29Z, content-freshness proven by addPluginsToRsbuildConfig serving TRUE post-drift span :175-205 rank#1), root `/mnt/hdd/utopia/inspo/frameworks/rsbuild`, branch main @ 2bcf61c (= base_sha = head_sha), full mode, parse_partial ×28 all e2e fixtures/website JSX/types re-export/template-solid JSX (none cited), skipped 0. Pass 1 (19 refs): runtime kernel — instance/plugins/hooks/config/server/HMR/assets/SSR. Pass 2 (+36 refs = 55): full-tree citation-vs-inventory grep over packages/core/src exposed ~60 never-cited files; whole-file reads of the built-in plugin suite (~30), server extras (middlewares/browserLogs/overlay/cliShortcuts/watchFiles/buildManager/historyApiFallback/previewServer/gracefulShutdown/httpServer), loaders trio, createCompiler/loadConfig/defaultConfig, helpers format/stats/path/fs, resource-hints quartet; all 43 newly cited paths `no_recorded_issue`+`metadata_match`; graph id-sweeps resolved 45 anchors line-exact; probes pinned to real suites (css.test externals.test minimize.test splitChunks.test swc.test sourceMap.test target.test helpers.test cliShortcuts.test overlay.test cache.test entry.test html.test asset.test + e2e server/html-fallback server/base-url browser-logs/* manifest/* security/sri-* security/nonce-* css/* assets/inline-query lazy-compilation/*). Coverage caveats recorded in-capsule where no direct suite exists at pin (sendStats ladder, watch-files, close ordering, clean-output edge table, history-fallback direct, loadConfig unit layer). Pass 4 (+6 = 64 @ 2bcf61c): drift re-entry executing queued target #3 — create-rsbuild/Octane scaffolder plane mined whole-file (src/index.ts + src/rsbuildConfig.ts + template corpus + e2e/cases/create-rsbuild suites); drift delta (#8353) itself was label/reorder-only, mined as part of template-wiring capsule; gate-5 REAL behavioral execution via node v26 type-stripping of rsbuildConfig.ts (empty-config seed, tailwind→compiler order snapshot byte-equal to upstream tools.test.ts, plus an adversarial double-write RED proving the cache-bypass hazard); coverage stdin-JSON ×7 all no_recorded_issue+metadata_match+generation_matches=true.

Pass 5 (2026-08-25, miner-rsbuild lane): pin re-verified live at `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5` (= base_sha, tree clean). Served graph found STALE at pass start (14,316n @ generation 2026-08-16T00:20:45Z; `metadata_changed` on 15/20 cited paths; span drift proven vs clean checkout — workerLoader −13 lines, rspackProfile +11, client overlay +2) → FULL in-place re-index of project `rsbuild` via explicit name override (a first attempt derived a path-slugged twin `mnt-hdd-utopia-inspo-rsbuild`, deleted immediately; no duplicate remains) → 14,580 nodes / 27,023 edges @ generation 2026-08-25T09:03:18Z, parse_partial ×28 all uncited fixtures. All 20 pass-5 cited paths `no_recorded_issue`+`metadata_match`; previously drifted spans now line-exact vs direct reads. Pass 5 (+7 refs = 71): uncited tail mined whole-file — transform loader pair, workerLoader+pluginWorker, nodeAddons, wasm, progress+rsdoctor+rspackProfile trio, pluginHelper+vendors, client overlay/log + server overlay/ansiHTML/hmrFallback plane. Boundaries amendment: the historical "remaining tiny loaders" omission above is superseded by these capsules; inspectConfig emission layout, cli/init.ts beyond :84, cli/commands.ts, and types/config.ts normalize* family remain deferred next-pass targets.

## Full view (memory graph)
Revalidate `rsbuild` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Pass 1: `index_status --project rsbuild --verbose` confirmed HEAD `ded92636…` = base_sha, mode full, freshness metadata_match on every cited path via stdin-JSON `check_index_coverage` (all `no_recorded_issue`). Pass 2 re-confirmed identical HEAD/counts/generation; id-sweeps resolved the pass-2 anchor set (`pluginCss normalizeCssLoaderOptions pluginSplitChunks getPackageNameFromModulePath composeAutoExternalRules getSwcMinimizerOptions parseMinifyOptions getInlineTests generateManifest HtmlResourceHintsPlugin recursiveChunkEntryNames formatBrowserErrorLog convertLinksInHtml renderErrorToHtml setupCliShortcuts setupWatchFiles BuildManager historyApiFallbackMiddleware createCompiler loadConfig defineConfig pluginLazyCompilation getBuildDependencies cssUrlLoader pitch ignoreCssLoader formatStatsError getStatsErrors dedupeNestedPaths emptyDir startPreviewServer setupGracefulShutdown createHttpServer getHtmlCompletionMiddleware getBaseUrlMiddleware getHtmlFallbackMiddleware pluginAppIcon pluginSri pluginNonce getDevtool normalizeCleanDistPath getServerUrlFromClientConfig getPublicPath applyAlias` — 45/45 line-exact). Pass-1 anchors (`createRsbuild`, `createPluginManager`, `sortPluginsByEnforce/Dependencies`, `createAsyncHook`, `createEnvironmentAsyncHook`, `initHooks`, `registerBuildHook`, `registerDevHook`, `initPluginAPI`, `initRsbuildConfig`, `generateRspackConfig`, `createContext`, `normalizeConfig`, `loadEnv`, `getPort`, `SocketServer`, `BuildManager`, `applyHMREntry`, `setupServerHooks`, `createAssetsMiddleware`, `getFileFromUrl`, `setupOutputFileSystem`, `setupWriteToDisk.resolveWriteToDiskConfig`, `gzipMiddleware`, `createProxyMiddleware`, `EsmRunner`, `CommonJsRunner`, `BasicRunner`, `asModule`, `loadBundle`, `getTransformedHtml`, `createCacheableFunction`, `findFirstUserFrame`, `getRsbuildStats`, `formatStats`, `removeLoaderChainDelimiter`, `printFileSizes`, `RsbuildHtmlPlugin`, `applyTagConfig`, `getTemplate`, `createCompileState`, `exitHook`, `createRestartManager`). `trace_path createRsbuild both` shows 69 callees spanning createContext/withDefaultConfig/initPluginAPI clusters; `trace_path initPluginAPI both` shows the six API factory closures and 26 caller hops.  Pass 3 drift re-entry (72 commits ded92636..bc19fd5e): diff-first triage split lint/format churn (type-aware prettier reflow across ~80 files) from four production clusters — dynamic-port plane, startup-failure rollback, hot-path perf cluster, splitChunks server flip; id-sweeps on the adopted twin resolved `resolvePort` 498–520, `inheritPort`/`setPort` 36–45, `sortTags` 106–110 line-exact. Pass 4 drift re-entry (bc19fd5e..2bcf61c, 2 commits): in-place twin re-index (14,580n/27,023e) with content-freshness proven by span agreement — `addPluginsToRsbuildConfig` :175-205, `getTemplateName` :23-60, `enableReactCompilerInRsbuildConfig` :207-216, `addCalls` :126-157 all rank#1 line-exact at TRUE source spans; the drift delta itself (#8353 label/reorder + #8352 docs) carried no new symbols, so span-match is the freshness proof. Source and direct tests decide shipped claims.

Pass-5 retrieval evidence: post-reindex GREEN `resolveHostname` rank#1 (hmrFallback.ts 23–35 line-exact) and adversarial RED "fallback when websocket disconnects reconnect" (20 hits, hmrFallback.ts ABSENT — misleading filename, capsule vocabulary required) each observed twice across index generations; `compileInlineWorker` 92–211 / `getInlineWorkerWrapper` 45–84 line-exact after refresh; nodeAddons/wasm/progress/rsdoctor served spans matched direct reads byte-for-byte both pre- and post-reindex. Deterministic probe pins executed via grep: wasm `.dependency('url')` :24; progress spread-order :23; rsdoctor gate :20; profile `void …cleanup()` :132; raw twin `export const raw = true` transformRawLoader.ts:6; worker eager-import workerLoader.ts:129; overlay dedup client/overlay.ts:219; pipeline order server/overlay.ts:104; verbatim DNS lookup hmrFallback.ts:15; native branch pluginHelper.ts:14; socketServer dual payload :310.

## Boundaries
Adopt the pure contracts: plugin meta-store + ordering algorithms, hook engine semantics, merge path-policy table, action state machine, token-gated socket protocol decision ladder, deferred compile-state, restart cleanup-swap, HTTP caching/security ladder, vm bundle runner; pass-2 additions: twin importLoaders counters, postcssrc promise-cache + creator invocation, pitch-phase ?url child build, ignore-css module-export gate, pure_funcs console removal, autoExternal regex compiler with worker wipe, additive SWC includes + target/env exclusivity, splitChunks dispatcher/presets with diverging server(split)/worker(off) defaults, explicit buildDependencies invalidation, lazy serverUrl origin-following, intent-first asset oneOf ladders, mark-then-sweep inline deletion w/ map rescue, entrypoint-vs-chunk manifest partitioning, resource-hint dedupe algebra, SRI/nonce dual-path CSP pairing, define env-leak probe, devtool/extract decision tables, strict-subdir clean gates, HTML completion/fallback/base ladder, stack-symbolication tiers, four-tap compiler state machine, ordered teardown + refcounted signals, TTY-gated shortcuts, grouped watchers, first-compile publicDir copy, config-function params contract, factory defaults. Adapt host-specific details: logger colors, Rspack/rspack-chain integration points, connect-next middleware host, CLI option surface, concrete dist paths/ports/decorator defaults. Omit product surface: website/docs, e2e case fixtures (harness PATTERNS captured in `e2e-harness-fixtures`; the create-rsbuild e2e SUITE itself is now capsuled in `create-e2e-harness`), per-framework plugin packages (react/vue/svelte/less/sass/svgr/tailwind/preact/solid/babel) which follow the same `RsbuildPlugin` contract already captured here, cli/index.ts banner UX, open.ts AppleScript ladder, inspectConfig emission layout, types/config.ts declarative normalize* family (sampled only — verify against source on a config-porting question), remaining tiny loaders (transformLoader/workerLoader/cssUrl siblings cited via css plane). Pass-4 retraction: the standing "omit create-rsbuild scaffolding templates" boundary is RETRACTED to the extent mined this pass — template wiring, config text-rewrite kernel, tool actions, Octane plane, corpus conventions, and the scaffolder e2e harness are now capsuled; remaining omission covers only `bin.js`, npm-publish packaging metadata, and the external `@rstackjs/create-toolkit` kernel itself.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`app-icon-pwa-plane.md`](./app-icon-pwa-plane.md)
- [`asset-query-ladder.md`](./asset-query-ladder.md)
- [`assets-middleware.md`](./assets-middleware.md)
- [`async-hook-engine.md`](./async-hook-engine.md)
- [`browser-error-overlay-plane.md`](./browser-error-overlay-plane.md)
- [`browser-logs-symbolication.md`](./browser-logs-symbolication.md)
- [`build-manager-shutdown.md`](./build-manager-shutdown.md)
- [`cache-build-dependencies.md`](./cache-build-dependencies.md)
- [`clean-dist-gates.md`](./clean-dist-gates.md)
- [`cli-shortcuts-readline.md`](./cli-shortcuts-readline.md)
- [`compile-state-env-api.md`](./compile-state-env-api.md)
- [`compiler-hooks-bridge.md`](./compiler-hooks-bridge.md)
- [`compiler-lifecycle-taps.md`](./compiler-lifecycle-taps.md)
- [`config-init-pipeline.md`](./config-init-pipeline.md)
- [`config-loading-contract.md`](./config-loading-contract.md)
- [`config-merge-semantics.md`](./config-merge-semantics.md)
- [`config-text-rewrite-kernel.md`](./config-text-rewrite-kernel.md)
- [`context-model.md`](./context-model.md)
- [`create-e2e-harness.md`](./create-e2e-harness.md)
- [`create-toolkit-template-wiring.md`](./create-toolkit-template-wiring.md)
- [`css-import-loaders-counter.md`](./css-import-loaders-counter.md)
- [`css-postcssrc-cache-wrapper.md`](./css-postcssrc-cache-wrapper.md)
- [`css-url-loader-pitch.md`](./css-url-loader-pitch.md)
- [`default-config-skeleton.md`](./default-config-skeleton.md)
- [`define-env-leak-guard.md`](./define-env-leak-guard.md)
- [`dev-server-lifecycle.md`](./dev-server-lifecycle.md)
- [`dynamic-port-restart-handoff.md`](./dynamic-port-restart-handoff.md)
- [`e2e-harness-fixtures.md`](./e2e-harness-fixtures.md)
- [`entry-registration-guard.md`](./entry-registration-guard.md)
- [`env-gated-diagnostic-plugins.md`](./env-gated-diagnostic-plugins.md)
- [`env-loading.md`](./env-loading.md)
- [`externals-auto-rules.md`](./externals-auto-rules.md)
- [`file-size-report.md`](./file-size-report.md)
- [`history-fallback-rewrite-ladder.md`](./history-fallback-rewrite-ladder.md)
- [`hmr-client.md`](./hmr-client.md)
- [`hot-path-projection-caches.md`](./hot-path-projection-caches.md)
- [`html-fallback-ladder.md`](./html-fallback-ladder.md)
- [`html-pipeline.md`](./html-pipeline.md)
- [`html-plugin-implementation-singleton.md`](./html-plugin-implementation-singleton.md)
- [`ignore-css-pitch-gate.md`](./ignore-css-pitch-gate.md)
- [`inline-chunk-mark-sweep.md`](./inline-chunk-mark-sweep.md)
- [`instance-assembly.md`](./instance-assembly.md)
- [`lazy-compilation-server-url.md`](./lazy-compilation-server-url.md)
- [`manifest-entry-partition.md`](./manifest-entry-partition.md)
- [`middleware-stack.md`](./middleware-stack.md)
- [`minify-removeconsole-purefuncs.md`](./minify-removeconsole-purefuncs.md)
- [`node-addons-transform.md`](./node-addons-transform.md)
- [`octane-template-plane.md`](./octane-template-plane.md)
- [`output-publicpath-ladder.md`](./output-publicpath-ladder.md)
- [`path-fs-kernels.md`](./path-fs-kernels.md)
- [`plugin-api-surface.md`](./plugin-api-surface.md)
- [`plugin-ordering.md`](./plugin-ordering.md)
- [`react-compiler-config-surgery.md`](./react-compiler-config-surgery.md)
- [`resolve-dedupe-alias.md`](./resolve-dedupe-alias.md)
- [`resource-hints-links.md`](./resource-hints-links.md)
- [`restart-shutdown.md`](./restart-shutdown.md)
- [`server-public-dir-copy.md`](./server-public-dir-copy.md)
- [`socket-server-hmr.md`](./socket-server-hmr.md)
- [`sourceMap-extract-ladder.md`](./sourceMap-extract-ladder.md)
- [`split-chunks-dispatcher.md`](./split-chunks-dispatcher.md)
- [`sri-nonce-security.md`](./sri-nonce-security.md)
- [`ssr-bundle-runner.md`](./ssr-bundle-runner.md)
- [`startup-failure-rollback.md`](./startup-failure-rollback.md)
- [`stats-error-formatter.md`](./stats-error-formatter.md)
- [`swc-script-rule-assembly.md`](./swc-script-rule-assembly.md)
- [`tailwind-tool-action.md`](./tailwind-tool-action.md)
- [`target-browserslist-short-circuit.md`](./target-browserslist-short-circuit.md)
- [`template-corpus-conventions.md`](./template-corpus-conventions.md)
- [`transform-pipeline-loaders.md`](./transform-pipeline-loaders.md)
- [`wasm-url-dependency-rule.md`](./wasm-url-dependency-rule.md)
- [`watch-files-groups.md`](./watch-files-groups.md)
- [`worker-loader-inline-child-compiler.md`](./worker-loader-inline-child-compiler.md)
