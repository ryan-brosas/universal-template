---
name: uvicorn-foundation
description: "Use when porting an asyncio request-response server (HTTP/1.x, HTTP/2, WebSocket) or building the supervising shell around one — process lifecycle, graceful shutdown, worker fleets, protocol negotiation, backpressure, and proxy-trust boundaries. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
disable-model-invocation: true
---
# Uvicorn: ASGI server kernel (lifecycle, supervision, protocol implementations)

## Use this for
Use when porting an asyncio request-response server (HTTP/1.x, HTTP/2, WebSocket) or building the supervising shell around one — process lifecycle, graceful shutdown, worker fleets, protocol negotiation, backpressure, and proxy-trust boundaries. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/shutdown-choreography.md` — In what order does the server stop accepting, drain connections/tasks, and replay signals?
- `references/max-requests-jitter.md` — Why does each worker pick a private randomized request limit at startup?
- `references/config-load-middleware-stack.md` — What wrap order turns a user app into the served object, and why can't it change?
- `references/asgi2-sniffing.md` — How does auto interface detection distinguish ASGI3 from ASGI2 without running the app?
- `references/header-preencoding.md` — Why are custom headers lowercased latin-1 at load time, and who refreshes the Date header?
- `references/supervisor-dispatch-import-gate.md` — When must the app be an import string, and who binds the shared socket?
- `references/zero-downtime-restart-ladder.md` — Why does the replacement worker start BEFORE the old worker dies?
- `references/signal-queue-supervisor.md` — How do OS signals become named handlers without running work on the signal stack?
- `references/pipe-healthcheck-ping-pong.md` — How does the parent distinguish hung from ready workers via a tri-state pipe probe?
- `references/spawn-subprocess-bootstrap.md` — What must run again inside every worker child before the server starts?
- `references/reload-strategy-split.md` — How do watchfiles and stat fallback share one restart skeleton, and what is the .* special case?
- `references/flow-control-admission.md` — When does backpressure pause reads, and why is the 503 a fake ASGI app rather than a branch?
- `references/http-pipelining-deque.md` — Where do requests parsed mid-response wait, and what starts them in order?
- `references/h11-paused-pipelining-twin.md` — What replaces the deque when the parser itself buffers pipelined requests?
- `references/http-framing-rules.md` — When is chunked encoding auto-added, and which app header forces connection close?
- `references/lazy-100-continue.md` — Why is Expect: 100-continue answered only when the app first reads the body?
- `references/lifespan-auto-fallback.md` — How does a lifespan-less app still boot, and how is startup state shared with request scopes?
- `references/reset-contextvars-dual-branch.md` — Why does the contextvars leak workaround differ between Python 3.10 and 3.11+?
- `references/ws-upgrade-relay.md` — What bytes are replayed to hand a live HTTP transport to a WebSocket protocol?
- `references/ws-keepalive-fsm.md` — What keeps the ping loop alive with vs without ping_timeout, and how are stale pongs rejected?
- `references/ws-close-handshake.md` — Who closes first, what disconnect codes are synthesized, and why must send() never hang on a dead socket?
- `references/ws-accept-date-strip.md` — Why is the library's handshake Date deleted before merging accept headers?
- `references/websockets-legacy-inversion.md` — Why does the ASGI app start BEFORE the handshake in the websockets-legacy backend?
- `references/wsproto-buffer-errors.md` — How is ws_max_size enforced across fragments, and what closes on protocol errors?
- `references/proxy-trust-walk.md` — Why is X-Forwarded-For scanned right-to-left, and what makes a hop trusted?
- `references/wsgi-bridge-threading.md` — What runs on the executor vs the loop when streaming a sync WSGI app into ASGI?
- `references/zttp-framing-ladder.md` — Which response headers are dropped or rewritten when the parser is strict?
- `references/h2-stream-multiplexing.md` — How do per-stream cycles, GOAWAY, and cross-stream read gating extend the HTTP/1 model?
- `references/h2-negotiation-preface.md` — When is the protocol chosen from TLS metadata vs sniffed bytes?

## Capsule map

### Lifecycle & supervision
- **Shutdown choreography** — `shutdown-choreography`: listeners→connections→tasks(0.1s poll ladder, timeout-cancel)→lifespan; captured signals re-raised LIFO after handler restore; second SIGINT = force_exit.
- **Max-requests jitter** — `max-requests-jitter`: cached_property draws `limit + randint[0..jitter]` once per worker so N workers recycle staggered.
- **Supervisor dispatch & import gate** — `supervisor-dispatch-import-gate`: reload/workers REQUIRE import string (children re-import); parent binds socket once; UDS removed in finally; STARTUP_FAILURE=3 exit contract.
- **Zero-downtime restart ladder** — `zero-downtime-restart-ladder`: start-new → wait-ready(pipe) → kill-old per slot; failed replacement aborts whole rotation keeping veterans.
- **Signal-queue supervisor** — `signal-queue-supervisor`: handlers only append signum to a list; 0.5s tick drains snapshot and dispatches by `handle_<name>` lookup.
- **Pipe healthcheck** — `pipe-healthcheck-ping-pong`: send b"ping", bounded poll → bool started | None; None collapses every transport failure to "unhealthy".
- **Spawn bootstrap** — `spawn-subprocess-bootstrap`: allow_connection_pickling at import; child reopens stdin fileno + re-runs configure_logging before target.
- **Reload strategy split** — `reload-strategy-split`: BaseReload owns restart skeleton + delay-bounded pause; watchfiles/stat strategies supply should_restart; patterns inert without watchfiles.

### Config & app adaptation
- **Config.load middleware stack** — `config-load-middleware-stack`: factory call-then-check → interface detect → WSGI/ASGI2 adapter → TRACE logger → ProxyHeaders outermost; computed once behind `assert not loaded`.
- **ASGI2 sniffing** — `asgi2-sniffing`: class `__await__` / function coroutine-check / instance `__call__` static probe; partial-tolerant predicate choice.
- **Header pre-encoding** — `header-preencoding`: lowercase latin-1 once at load; user `Server:` suppresses default; Date rebuilt once/second in the tick loop.
- **Lifespan auto-fallback** — `lifespan-auto-fallback`: auto+BaseException = info-log-and-serve; explicit on = fatal; state dict copied per request scope; events always set in finally.
- **reset_contextvars dual branch** — `reset-contextvars-dual-branch`: `create_task(context=Context())` ≥3.11 vs `Context().run(create_task, …)` below; identical isolation, different mechanics.

### Protocol kernel (shared)
- **FlowControl & admission** — `flow-control-admission`: 64KiB body high-water pauses transport reads; limit_concurrency OR-gate swaps in a canned service_unavailable app at headers-complete.
- **Lazy 100-continue** — `lazy-100-continue`: interim response written inside first receive() and latched off; unread bodies never get 100.
- **Response framing rules** — `http-framing-rules`: tri-state chunked latch; neither CL nor TE ⇒ auto-chunk (except HEAD/204/304); length enforced both directions.
- **WS upgrade relay** — `ws-upgrade-relay`: discard-from-registry → synthesize raw request → new protocol.connection_made → data_received(replay) → set_protocol last.
- **WS close handshake** — `ws-close-handshake`: code synthesis 1005/1006/1012 by state; resume reads after sending close to catch the echo; connection_lost sets writable event (asyncio never resumes lost paused transports).

### Per-backend twins (SIMILAR_TO family)
- **httptools pipelining deque** — `http-pipelining-deque`: appendleft/pop FIFO of (cycle, app); reads paused while queued; keep-alive arms only when empty.
- **h11 PAUSED twin** — `h11-paused-pipelining-twin`: parser buffers next request ⇒ PAUSED arm pauses reads; ordering via DONE/DONE start_next_cycle + handle_events replay.
- **zttp framing conflict ladder** — `zttp-framing-ladder`: TE stripped on <200/204; CL dropped when both present; auto-chunk added when neither; should_close covers both directions.
- **H2 stream multiplexing** — `h2-stream-multiplexing`: cycles dict keyed by stream_id; GOAWAY latch refuses+drains; RstStream aborts ONE cycle; any over-limit stream holds transport reads; forbidden response headers silently stripped.
- **h2c preface / ALPN negotiation** — `h2-negotiation-preface`: TLS picks by ALPN; cleartext holds bytes while they prefix the 24-byte PRI magic then dispatches with buffered replay.
- **SansIO WS keepalive FSM** — `ws-keepalive-fsm`: random 4-byte payload tags each ping; pong must match payload; timeout mode chains via pong-cancel-reschedule, no-timeout mode schedules directly; RTT subtracted from next delay.
- **SansIO WS accept Date strip** — `ws-accept-date-strip`: websockets lib pre-stamps Date on its Response; delete-before-merge keeps exactly one; subprotocol appended after merge.
- **websockets-legacy inversion** — `websockets-legacy-inversion`: run_asgi launched inside process_request which blocks on handshake_started_event; process_subprotocol overridden to return the APP's choice.
- **wsproto buffer & error hints** — `wsproto-buffer-errors`: ws_max_size counted as UTF-8 BYTES across fragments (1009 close); RemoteProtocolError replays err.event_hint verbatim.

### Edge plane
- **Proxy trust walk** — `proxy-trust-walk`: direct peer must be trusted; XFF walked REVERSED for first untrusted hop else leftmost; literals/IPs/networks classified once; lru_cache(4096) with >253-char bypass.
- **WSGI bridge threading** — `wsgi-bridge-threading`: body buffered to BytesIO; app on ThreadPoolExecutor; chunks cross threads via queue + call_soon_threadsafe wakeup; a2wsgi preferred if installed.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Uvicorn (BSD-3-Clause), `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory project `ext-uvicorn` (ready FULL 1,758n/8,424e, head==base==worktree HEAD zero drift, parse_partial ×0, freshness proven via drift-introduced ZttpH2Protocol resolving line-exact; single project, no stale twin).

## Full view (memory graph)
Revalidate `ext-uvicorn` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/uvicorn`, branch main, commit 9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae, FULL mode, 1,758 nodes / 8,424 edges, generation matches source. SIMILAR_TO edges link the four HTTP impls and three WS impls — mine one pattern with its decisive instance and note twin deltas. Source and direct tests decide shipped claims. Note: BM25 retrieval ranks TEST functions highly for behavior queries — prefer symbol-name queries for impl sites.

## Boundaries
Adopt the lifecycle orderings (shutdown ladder, restart bring-up-before-retire, signal capture/replay) and the protocol state machines (framing latch, pipelining order, keepalive two-mode carrier, close-code synthesis) verbatim — these encode incident lessons and RFC constraints. Adapt transports and thresholds (pipe healthcheck → your IPC, 5s healthcheck timeouts, 64KiB high-water, 10s close ceiling). Omit product surfaces as out-of-scope: gunicorn workers.py shim (deprecated → uvicorn-worker package), click CLI option plumbing, ANSI logging colors, mkdocs/docs, win32 CTRL_C_EVENT dance when targeting POSIX only, and the deprecated native WSGI middleware body (a2wsgi supersedes it).
