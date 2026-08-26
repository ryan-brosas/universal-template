---
name: htmx-foundation
description: "Use when porting or embedding a hypermedia-driven AJAX/DOM kernel: attribute-inheritance ladder, trigger-spec grammar and dispatch FSM, extended selector engine, priority FormData collection with live proxy, request lifecycle with hx-sync queueing, response-handling table with HX-* control headers, swap/settle choreography with OOB + preserve pantry, hash-gated node processing, history cache LRU, boost/security gates."
disable-model-invocation: true
---
# htmx: Hypermedia Interaction Kernel Foundation

## Use this for
Porting htmx's interaction model into any host: declarative attributes (hx-get/post/put/delete/patch, hx-trigger, hx-target, hx-swap, hx-swap-oob, hx-sync, hx-boost, hx-vals/params/headers, hx-on:*), the event-veto pipeline that ties them together, and the browser-compat machinery (script re-creation, preserve pantry via moveBefore, settle-delayed attribute merge). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/attribute-inheritance-ladder.md` — closest-value lookup with hx-disinherit/hx-inherit and the `'unset'` sentinel.
- `references/response-fragment-parsing.md` — makeFragment's three parse paths, title hoisting, script duplicate-before-remove.
- `references/trigger-spec-grammar.md` — tokenizer + option loop for hx-trigger; defaults ladder; sharp edges (`from:` chevrons don't parse).
- `references/trigger-dispatch-fsm.md` — exact gate order (liveness→cancel→filter→once→consume→target→changed→delay/throttle) and polling/revealed arms.
- `references/extended-selector-engine.md` — closest/find/next/previous/global/root/host keywords + chevron-aware comma split.
- `references/value-collection-priority-formdata.md` — dual-lane FormData merge, submitter tracking, positional dedup.
- `references/formdata-proxy.md` — proxy trap matrix making values object-like while FormData-backed.
- `references/request-lifecycle-sync-queue.md` — click→send gate ladder and drop/abort/replace/queue strategies on the sync-element lock.
- `references/response-handling-control-plane.md` — status-code table plus HX-Retarget/-Reswap/-Reselect/-Location/-Redirect precedence.
- `references/swap-pipeline-settle.md` — doSwap/doSettle choreography: OOB sweep, select, preserve, focus restore, view transitions.
- `references/oob-swap-contract.md` — hx-swap-oob value grammar, multi-target clones, loud no-target error.
- `references/preserve-pantry.md` — state-preserving element parking via moveBefore with legacy fallback.
- `references/node-processing-init-hash.md` — attribute-hash idempotence for process(); symmetric teardown.
- `references/hxon-wildcard-handlers.md` — hx-on name grammar, lazy compilation, wipe-first re-registration.
- `references/event-system-extension-veto.md` — camel+kebab double dispatch, false-veto contract, extension registry.
- `references/history-cache-restore.md` — sessionStorage LRU with shrink-retry, privacy embargo, miss ladder.
- `references/boost-security-gates.md` — boost eligibility, selfRequestsOnly+validateUrl egress ladder, eval/script gates.
- `references/indicator-refcount-hygiene.md` — shared-indicator refcounts, disabled-elt ownership tags, empty-class removal.
- `references/validation-ladder.md` — direct-submission-only validation gate and halted-before-open ordering.
- `references/config-boot-sequence.md` — boot order, meta-config merge, internalAPI handed to extensions.
- `references/polling-revealed-scheduling.md` — every-polling self-rearm, scroll-latch reveal scan, intersect indirection.
- `references/headers-trigger-protocol.md` — five mandatory request headers, URI-encoded fallback, three-phase HX-Trigger* timing.
- `references/swap-spec-parsing.md` — hx-swap modifier grammar: first-positional style, direction-last selectors, junk tolerance.
- `references/params-filtering-encoding.md` — hx-params allowlists and the extension→multipart→urlencoded encoder ladder.
- `references/gettarget-resolution.md` — target defaults, ancestor-owned `'this'`, boosted-body fallback.
- `references/shouldcancel-ladder.md` — preventDefault rules for forms/buttons/links with fragment-anchor and ctrl-click carve-outs.

## Capsule map
- **Attribute semantics** — `attribute-inheritance-ladder.md`: nearest-wins inheritance where own attrs always apply, disinherit blocks named/all, strict mode inverts default, `'unset'` sentinel converts to undefined only at the final check. `gettarget-resolution.md`: hx-target = closest-value → this(ancestor-owned)/selector → boosted body → self.
- **Parsing plane** — `response-fragment-parsing.md`: head-strip → html/body/template dispatch → title hoist → script normalize-or-strip. `trigger-spec-grammar.md`: token stream → every-vs-event specs with delay/throttle/from/target/queue/root/threshold modifiers; defaults submit/click/change by tag. `extended-selector-engine.md`: keyword prefixes + chevron counting so commas inside `<div/>` survive. `swap-spec-parsing.md`: style must be token 0; scroll:/show: take [selector:]direction with direction LAST.
- **Trigger runtime** — `trigger-dispatch-fsm.md`: fixed gate order makes once/consume/changed/delay/throttle compose; listeners attach to from:-elements but die with the subject. `polling-revealed-scheduling.md`: setTimeout self-rearm guarded by bodyContains+cancelled (286 cancels); one global 200ms scroll latch feeds revealed checks; intersect observers emit normal events.
- **Data plane** — `value-collection-priority-formdata.md`: non-GET pulls related form into priority lane; submitter value rides lastButtonClicked (focusin-tracked); overrideFormData merges lanes after positional dedup. `formdata-proxy.md`: get 0/1/N → undefined/scalar/array-proxy; set replaces whole key; toJSON/ownKeys/symbol-brand traps pinned by tests. `params-filtering-encoding.md`: inherited hx-params filter (none/*/not/list) then extension→multipart(proxy-materialized!)→urlencoded encoders.
- **Request plane** — `request-lifecycle-sync-queue.md`: confirm→sync(prompt/confirm skipped)→values→configRequest(mutable,copy-back)→validate-halt→verifyPath ladder; lock on sync elt with queue first/last/all ('last' dumps). `headers-trigger-protocol.md`: HX-Request/Trigger/Trigger-Name/Target/Current-URL always; setRequestHeader throw ⇒ URI-encoded + `-URI-AutoEncoded` tag; response triggers fire pre-load/after-swap/after-settle with body fallback. `boost-security-gates.md`: anchors(local,self-target)+non-dialog forms eligible; GET action query stripped; selfRequestsOnly default-deny egress vetoable via htmx:validateUrl; eval gates wrap conditionals/hx-on/js-prefixes; scripts duplicated-with-nonce or stripped.
- **Response & swap** — `response-handling-control-plane.md`: regex status table (204-no-swap / [23].. / [45]..-error) then header overrides; bad HX-Retarget THROWS; history decision HX-Push≻Push-Url≻Replace-Url≻attrs≻boosted-default. `swap-pipeline-settle.md`: fragment→selectOOB→OOB sweep→hx-select→preserve→style-dispatch(extension hooks claim unknown styles)→focus-by-id→settle tasks(attribute clone-back, ajax-load/process/focus per node). `oob-swap-contract.md`: true/style/style#sel grammar, per-target clones, strip-attribute-first, oobErrorNoTarget is loud but non-fatal. `preserve-pantry.md`: moveBefore pantry keeps iframe/media state; replaceChild fallback when absent.
- **Lifecycle & infra** — `node-processing-init-hash.md`: 32-bit Java-string-hash over non-empty attr name/value pairs gates deinit+init; firstInitCompleted survives so load fires once. `hxon-wildcard-handlers.md`: `:`/`-`/`htmx-` suffixes normalize to htmx: events; handlers lazy-compile under allowEval and wipe before re-register. `event-system-extension-veto.md`: same-detail kebab mirror dispatch unless identical; extensions resolved per-call up the hx-ext walk can veto anything by returning false. `history-cache-restore.md`: one sessionStorage key, size-capped shift-LRU, quota shrink-retry, `[hx-history=false]` embargo, miss→GET(HX-History-Restore-Request) or reload. `indicator-refcount-hygiene.md`: requestCount on shared targets, data-disabled-by-htmx ownership, empty-class-attribute removal. `validation-ladder.md`: validate only direct form submits (noValidate/formNoValidate respected); halted BEFORE xhr.open. `config-boot-sequence.md`: metaConfig→styles→process(body)→abort delegate→popstate chain→deferred htmx:load; internalAPI = extension superpower. `shouldcancel-ladder.md`: innermost-target-first preventDefault with fragment-anchor and ctrl-click carve-outs.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
htmx (BSD 2-Clause, `master@ad56dff71e55d9c717447437b4c942a64575d4b2`, v2.0.10 single-kernel layout: src/htmx.js 5,342 lines); Codebase Memory project `ext-htmx` (full index: 3,285 nodes / 8,011 edges, head == base_sha == disk HEAD ad56dff7, ready; parse_partial x7 confined to www/manual HTML, none cited; not_indexed: .git, dist/, www/static/node_modules). All 26 cited source paths and ~60 named test blocks read directly at pin; 40+ expectations additionally executed headless (Node vm shim battery: parseInterval, tokenizer 9/9, trigger-spec shapes, swap-spec S1-S4, disinherit/unset matrix, formDataProxy set/get/delete, urlEncode arrays, resolveResponseHandling table). Browser runner BLOCKED this window (repo ships web-test-runner/playwright; node_modules absent) — recorded as caveat, never fabricated as pass.

## Full view (memory graph)
Revalidate `ext-htmx` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/htmx`, branch master @ `ad56dff71e55d9c717447437b4c942a64575d4b2` (head==base_sha, fresh, FULL mode, ready), 3,285 nodes / 8,011 edges. Caveats: www/static/src/htmx.js and www/themes/.../htmx.js are DIST TWIN copies of the kernel that pollute BM25 results (e.g. oobSwap query returns all three at identical line ranges) — filter hits to `src.htmx.*`; test/ files are indexed but JS-test symbols carry little BM25 weight, cite them from disk reads. Every Retrieve block in references was executed rank-1 line-exact against this project during authoring.

## Boundaries
Adopt the pure contracts: inheritance ladder, spec grammars, dispatch orderings, refcount bookkeeping, cache LRU semantics, proxy trap matrix, and the veto-by-false event protocol. Adapt DOM-specific mechanics (moveBefore pantry, template wrapping, CSS injection, XHR arms) to your host's primitives; keep ordering identical because event-timing bugs reduce to reorderings. Omit product surfaces you don't need: hx-boost full-page mode, WebSocket/SSE (separate repos in the htmx ecosystem), the www site, and IE-era fallbacks beyond those tests pin.
