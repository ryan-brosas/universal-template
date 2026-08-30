---
name: requests-foundation
description: "Use when porting psf/requests internals — session orchestration, transport adapter/pool plane, redirect/auth/proxy state machines, prepared-request pipeline, and response consumption contracts."
disable-model-invocation: true
---

# requests: Foundation

## Use this for
Use when porting requests-style HTTP client machinery into another codebase: a Session with setting-merge semantics and longest-prefix adapter dispatch, the urllib3 adapter boundary (pool-key derivation, exception translation, proxied URL shaping), redirect resolution with credential-leak guards, cookie-jar bridging over stdlib http.cookiejar, the PreparedRequest stage pipeline with body framing rules, and streamed-response consumption with error remapping. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/session-setting-merge.md` — four-arm precedence for request-vs-session settings; None strips the key; merge_hooks empty-list suppression.
- `references/adapter-prefix-mount.md` — mount maintains longest-prefix-first insertion order; get_adapter first-match dispatch.
- `references/session-redirect-resolution.md` — per-hop drain→cap→close→normalize→rebuild choreography and history slicing.
- `references/session-strip-auth.md` — should_strip_auth decision table incl. http→https standard-port carve-out; netrc re-application order.
- `references/session-rebuild-method.md` — 303/302 downgrade-all-except-HEAD, 301 downgrades POST only, 307/308 untouched.
- `references/session-rebuild-proxies.md` — strip Proxy-Authorization before re-evaluating; never inject into TLS tunnels.
- `references/session-environment-settings.md` — trust_env proxies via setdefault; REQUESTS_CA_BUNDLE only overrides unset verify.
- `references/session-send-pipeline.md` — send stage ordering: guard→adapter→elapsed→hooks→cookies→redirects→assembly→consume.
- `references/session-next-lookahead.md` — yield_requests lookahead populates Response.next with full rebuild side effects.
- `references/cookies-mock-bridge.md` — MockRequest/MockResponse adapt PreparedRequest+urllib3 to stdlib CookieJar extract/add.
- `references/cookie-jar-dict-facade.md` — RequestsCookieJar O(n) dict ops, conflict vs default, None-deletes, pickle lock dance.
- `references/adapter-error-taxonomy.md` — MaxRetryError reason-type dispatch incl. NewConnectionError exclusion; hierarchy-as-API.
- `references/adapter-pool-manager.md` — Retry(0, read=False) default; poolmanager pickle contract; per-proxy manager cache.
- `references/adapter-tls-pool-keys.md` — verify/cert land in PoolKeys so TLS changes fork pools; get_connection_with_tls_context migration.
- `references/adapter-cert-verify.md` — bundle existence fail-fast; explicit CA-state clearing on verify=False for reused connections.
- `references/adapter-request-url-shaping.md` — absolute-form only for plaintext-http-through-proxy; urldefragauth strips creds.
- `references/adapter-send-prelude.md` — chunked predicate, strict timeout-tuple error, four load-bearing urlopen flags.
- `references/adapter-build-response.md` — field mapping defaults, encoding-from-headers precedence, connection back-reference requirement.
- `references/models-prepare-order.md` — seven fixed stages; auth before hooks (both documented); Content-Length recomputed post-auth.
- `references/models-body-preparation.md` — json/data/files/stream tree; allow_nan=False; tri-state _body_position rewind contract.
- `references/models-url-preparation.md` — non-http bypass, IDNA/wildcard host gates, param merging, whole-URL requote.
- `references/response-content-plane.md` — iter_content exception remaps, tri-state _content, iter_lines pending-line rule, json BOM path.
- `references/utils-proxy-selection.md` — four-key proxy precedence; NO_PROXY anchored-suffix + CIDR ladder (bpo-39057).
- `references/utils-super-len.md` — remaining-bytes probe ladder with position restore and two OSError adjudications.
- `references/utils-netrc-auth.md` — $NETRC override, .netrc/_netrc fallback, fail-silent posture, account-slot login fallback.
- `references/utils-requote-uri.md` — unquote-unreserved then quote with %-safe list; bare-percent fallback differs by exactly one char.
- `references/utils-json-charset.md` — BOM-first then null-position utf-8/16/32 detection from four bytes.
- `references/auth-digest-state-machine.md` — threading.local nonce state, one-shot 401 retry cap, resend via r.connection.send.
- `references/hooks-dispatch-contract.md` — single-callable tolerance, None-pass-through chaining, pre-cookie/pre-redirect timing.
- `references/exceptions-hierarchy-context.md` — RequestException context back-fill; ConnectTimeout/ContentDecodingError diamond roots.
- `references/structures-header-plane.md` — CaseInsensitiveDict tuple-store design; prepare-time header regex validation.
- `references/session-shutdown-cascade.md` — with-block exit → Session.close → per-adapter poolmanager+proxy_manager clear.
- `references/response-lifecycle-close.md` — close releases unconsumed raw + always release_conn; pickling forces consumption.
- `references/response-ok-raise-plane.md` — raise windows are exactly 4xx/5xx; bytes reason utf-8→latin fallback; bool(response)==not-error.
- `references/utils-header-links.md` — `, *<` entry split, one-`;` URL/params split, no-= truncates remaining params; rel-keyed with url fallback.
- `references/utils-unicode-streaming.md` — encoding-None passes bytes through; incremental decoder + final flush; replay re-slices memoized _content.
- `references/auth-basic-encoding.md` — latin-1 wire encode, deprecation shim for non-str, Proxy-Authorization subclass override.
- `references/structures-status-registry.md` — alias setattr registry with empty dict store; loud attr miss vs silent item miss.

## Capsule map
- **Session settings** — `session-setting-merge`: request wins scalars, dicts merge key-wise, final None deletes key; `[]` hooks suppress session hooks.
- **Adapter dispatch** — `adapter-prefix-mount`: OrderedDict reorder keeps longest prefixes first; first case-insensitive prefix match wins.
- **Redirect loop** — `session-redirect-resolution`: force-drain body, cap at max_redirects, close, normalize scheme-less/fragment/relative, rebuild everything, rewind streamable bodies.
- **Auth stripping** — `session-strip-auth`: hostname change strips; 80/None→443/None upgrade kept; default-port equivalence; netrc re-arms after strip.
- **Method rewrite** — `session-rebuild-method`: 303&302 →GET unless HEAD; 301 →GET only from POST.
- **Proxy rebuild** — `session-rebuild-proxies`: delete stale Proxy-Authorization, re-inject from proxy URL only on non-https hops.
- **Env settings** — `session-environment-settings`: env fills gaps via setdefault; CA-bundle env vars never resurrect verify=False.
- **Send pipeline** — `session-send-pipeline`: elapsed measures adapter only; hooks before cookies/history; history assembly rotates last forward; non-stream forces content.
- **Next lookahead** — `session-next-lookahead`: yield_requests=True yields rebuilt PreparedRequest stored as r._next under StopIteration tolerance.
- **Cookie bridge** — `cookies-mock-bridge`: urllib2-shaped mock over PreparedRequest; _original_response guard no-ops synthetic responses.
- **Cookie facade** — `cookie-jar-dict-facade`: conflict-raising lookups, None-unset, quoted-value unwrap, RLock dropped/restored around pickling.
- **Error taxonomy** — `adapter-error-taxonomy`: MaxRetryError.reason type dispatch with NewConnectionError exclusion; unknown HTTPErrors re-raised bare.
- **Pool construction** — `adapter-pool-manager`: save-scalars-then-build for pickling; Retry(0, read=False) means connect-only retries; proxy managers cached per URL.
- **TLS pool keys** — `adapter-tls-pool-keys`: cert_reqs/ca_certs/ca_cert_dir/cert_file/key_file in PoolKey; four-key proxy selection feeds connection_from_host.
- **Cert verification** — `adapter-cert-verify`: missing bundles raise OSError pre-connect; disabled verify explicitly nulls all CA fields.
- **URL shaping** — `adapter-request-url-shaping`: origin-form everywhere except plaintext-http-via-non-SOCKS-proxy (absolute-form, cred-stripped).
- **Send prelude** — `adapter-send-prelude`: chunked iff body-without-CL; 2-tuple timeouts strict; urlopen pinned redirect/preload/decode off, assert_same_host off.
- **Response build** — `adapter-build-response`: getattr-defaulted field copies, encoding precedence at build time, response.connection = self is digest-auth's resend path.
- **Prepare order** — `models-prepare-order`: method→url→headers→cookies→body→auth→hooks with both ordering comments normative.
- **Body framing** — `models-body-preparation`: json-only w/ allow_nan=False; streams record tell() or object() sentinel; files XOR streams; CL-or-chunked.
- **URL preparation** — `models-url-preparation`: non-http colon URLs pass verbatim; MissingSchema/InvalidURL gates; IDNA uts46 or wildcard rejection; params append then requote.
- **Content plane** — `response-content-plane`: ProtocolError→ChunkedEncoding etc. mid-stream; False/None/bytes tri-state; pending-line holdback across chunks.
- **Proxy selection** — `utils-proxy-selection`: scheme://host > scheme > all://host > all; no_proxy CIDR/literal/dot-anchored suffix; platform bypass scoped.
- **Length probing** — `utils-super-len`: __len__/.len/fstat/tell/seek-end ladder returning remaining bytes, restoring seek position.
- **Netrc** — `utils-netrc-auth`: $NETRC alone else dotfiles in order; parse errors silent unless raise_errors; account slot as login fallback.
- **Requoting** — `utils-requote-uri`: decode-unreserved scan; primary quote keeps % safe; fallback encodes bare % by dropping it from safe.
- **JSON charset** — `utils-json-charset`: BOM checks (incl. -sig) precede null-count endian heuristics.
- **Digest auth** — `auth-digest-state-machine`: cached-nonce fast path, body-position rewind, num_401_calls<2 single retry, resend on same connection.
- **Hooks** — `hooks-dispatch-contract`: normalized lists, replacement-on-truthy-return chaining, loud unknown-event ValueError.
- **Exceptions** — `exceptions-hierarchy-context`: context back-fill from response; diamond classes encode catch-site retry semantics; JSONDecodeError reduce override.
- **Headers/CID** — `structures-header-plane`: lowercase-indexed (casedKey,value) tuples preserve wire casing; validators reject bad name/value chars pre-store.
- **Shutdown cascade** — `session-shutdown-cascade`: Session.close iterates adapters; each adapter clears poolmanager AND every cached proxy manager.
- **Response close** — `response-lifecycle-close`: raw.close only when unconsumed, release_conn always; pickling consumes body and nulls raw.
- **ok/raise plane** — `response-ok-raise-plane`: raise iff status in [400,600); bytes reason utf-8→iso-8859-1; `.ok` swallows HTTPError; bool delegates.
- **Link headers** — `utils-header-links`: split entries on `, *<`; first `;` splits URL/params; param without `=` truncates the rest of its entry.
- **Unicode streaming** — `utils-unicode-streaming`: encoding None yields bytes unchanged; incremental decoder buffers partial chars, flushes with final=True.
- **Basic auth** — `auth-basic-encoding`: str creds encoded latin-1 (never utf-8); non-str shim warns+str(); HTTPProxyAuth swaps header name only.
- **Status registry** — `structures-status-registry`: aliases setattr'd into instance __dict__; dict store stays empty; attr miss raises, item miss Nones.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
psf/requests (Apache-2.0), `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory project `requests` (ready FULL, 1,428 nodes / 5,663 edges, generation 2026-08-25T19:56:35Z, head==base==working-tree HEAD zero drift, parse_partial ×1 tox.ini uncited; prior passes used the now-dead project name `ext-requests` at the same HEAD — always re-check `list_projects` before citing). BM25 recall thin for some bare method names — use a `def <name>` query fallback noted in affected capsules.

## Full view (memory graph)
Revalidate `requests` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph labels skew toward Method/Function/Class nodes; TESTS edges (722) make tests/test_requests.py an effective hub when tracing seam coverage.

## Boundaries
Adopt pure client-side contracts: merge ladders, state machines, framing decisions, exception tables, jar bridging. Adapt urllib3-specific pool/TLS plumbing to the host's connection library keeping the contract surfaces (flags, keys, back-references). Omit product packaging: api.py top-level sugar, help.py pager, certs.where() discovery details, Windows registry proxy internals, and the py2 compat shims flagged inside capsules.
