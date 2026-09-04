<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# gpt-researcher: Autonomous Research Pipeline Foundation

## Use this for
Use when building or porting systems that turn one question into a sourced report: planner-generated sub-query fan-out over swappable retrievers, snippet-vs-prefetched-content scraping, embedding-similarity context compression with small-input fast paths, MCP servers as first-class retrievers with LLM tool selection, recursive breadth×depth "deep research" descent under word budgets, and per-step cost attribution that prefers API-reported usage. Source code is ground truth; each capsule carries a decisive excerpt, invariant, executed probe, and graph retrieval.

## Load the matching source dump
### Orchestration & cost plane (`agent.py`, `utils/llm.py`, `utils/costs.py`)
- `./conduct-image-pregeneration-ladder.md` — deep-research branch gate, agent-selection-if-missing, images planned from finished context BEFORE writing, `_current_step` cost buckets (incl. the un-awaited log quirk).
- `./quick-search-multi-retriever-merge.md` — one-shot search fans out via exception-swallowing gather, dedups on the url/href alias identity.
- `./step-attributed-cost-ledger.md` — every `cost_callback` lands on both the run total and the `_current_step` bucket set by the orchestrator.
- `./llm-retry-temperature-ladder.md` — 10-attempt exponential backoff capped at 8s, frozen to 1 attempt once streaming starts, temperature suppressed for models that forbid it.
- `./provider-model-policy-tables.md` — NO_SUPPORT_TEMPERATURE / SUPPORT_REASONING_EFFORT model tables plus `stream_usage` so streamed calls still report real tokens.
- `./usage-first-cost-ladder.md` — Anthropic-native usage → OpenAI usage → tiktoken estimate; US inference-geo 1.1× surcharge; non-OpenAI embeddings fall back instead of raising.
### Research conductor plane (`skills/researcher.py`, `actions/query_processing.py`)
- `./report-source-dispatch-curator-failopen.md` — report_source ladder (source_urls→web→local→hybrid-gather→azure→langchain) and strict-JSON curation that fails open into string-normalized context.
- `./prefetch-content-split.md` — retriever `raw_content` >100 chars bypasses the scraper; scraped-then-extend merge order; random shuffle spreads scraper load.
- `./subquery-fanout-normalization.md` — json_repair'd planner output coerced into a flat `list[str]`; original query re-appended unless this IS a subtopic researcher.
- `./mcp-strategy-cache.md` — fast/deep/disabled strategy resolution with a lock-guarded one-shot MCP cache and Tavily-dual-path dedupe.
- `./session-scoped-mcp-wiring.md` — MCP configs append to `cfg.retrievers` never `os.environ`, so concurrent sessions cannot pollute each other.
- `./visited-url-dedup-contract.md` — shared `visited_urls` set deliberately survives across parent/subtopic researchers; hybrid passes run concurrently against it.
### Context compression plane (`context/compression.py`, `context/retriever.py`)
- `./compression-fast-path-thresholds.md` — ≤8000 chars AND few docs skips the whole LangChain compressor; otherwise split(1000/100)→EmbeddingsFilter at SIMILARITY_THRESHOLD 0.35.
- `./retriever-content-cap.md` — 50k-char per-document embed cap with `raw_content=None` coerced before slicing; scraper key `url` remapped to `source`.
### Scraping & throttling plane (`scraper/scraper.py`, `utils/workers.py`, `utils/rate_limiter.py`)
- `./browse-image-dedup-contract.md` — browse registers sources+images on the researcher; score-desc, content-hash + already-collected two-guard image selection (call-site k=4 beats signature default k=2).
- `./scraper-routing-dedupe.md` — path-only case-insensitive `.pdf` sniff beats arXiv beat configured backend; order-preserving URL dedupe; <100 chars nulled.
- `./global-rate-limiter-singleton.md` — one process-wide delay enforced while holding each pool's semaphore, so N researchers still respect one API quota.
### Deep research plane (`skills/deep_research.py`)
- `./deep-research-descent-budget.md` — breadth halves per depth level, concurrency-capped branches spawn child researchers sharing visited_urls/MCP config.
- `./context-word-budget-fold.md` — newest-first reverse fold keeps the recent window, truncates only an oversized head, drops older items wholesale.
- `./empty-descent-unbound-bug.md` — the zero-serp-queries early return reads locals assigned AFTER it: guaranteed UnboundLocalError on that path.
### Parsing & report plane (`agent_creator.py`, `deep_research.py` grammars, `actions/report_generation.py`, `skills/writer.py`, `utils/llm.py`, `backend/report_type/detailed_report`)
- `./json-rescue-grammars.md` — fenced/array/object regex extraction then line-grammar parsers; agent JSON rescued with GREEDY `{.*}` because non-greedy truncates.
- `./writer-abstention-gate.md` — empty gathered context returns a visible refusal, never a confident unsourced report.
- `./report-prompt-ladder-collapse-retry.md` — subtopic > custom > default prompt ladder with warn-and-default type resolution; pre-generated images appended to the USER message as verbatim markdown; one role-collapse retry for providers that reject system messages.
- `./auxiliary-write-failopen-empty.md` — intro/conclusion/URL-summary/draft-titles calls all degrade to ""/[] and never raise; draft titles hardcode websocket=None (never stream); summarize_url is an orphan export with zero internal callers.
- `./subtopics-fallback-shape-asymmetry.md` — Pydantic subtopic planner returns the model on success but the raw input LIST on failure; consumer survives only via truthiness-before-attribute-access on the empty default.
- `./detailed-report-subtopic-loop.md` — per-subtopic child researchers share ONE visited_urls set by aliasing; stringify-then-set-dedup context seed; two-sided dedup (retrieval of similar written contents + prompt-side uniqueness); references render only after URL merge.
- `./deterministic-references.md` — References section renders from `sorted(visited_urls)` because set iteration order broke report reproducibility.
### Registry & provider planes (`actions/retriever.py`, `memory/embeddings.py`, `mcp/*`)
- `./retriever-resolution-chain.md` — headers → config → default ladder with whitespace stripping and silent fallback for invalid names.
- `./embedding-provider-match-table.md` — 20-arm `match` statement where custom/lmstudio disables ctx-length checking and ollama REQUIRES its env var.
- `./mcp-tool-selection-fallback.md` — LLM picks ≤3 tools by index; any failure degrades to pattern-scored selection, never aborts.
- `./mcp-result-shape-normalizer.md` — every tool result collapses to `{title, href, body}` with `mcp://llm_analysis` pseudo-URLs skipped at citation time.

## Capsule map
- **Orchestration & cost** — `conduct-image-pregeneration-ladder`, `quick-search-multi-retriever-merge`, `step-attributed-cost-ledger`, `llm-retry-temperature-ladder`, `provider-model-policy-tables`, `usage-first-cost-ladder`: branch ladders route the loop, costs land once per step and prefer API-reported tokens.
- **Research conductor** — `report-source-dispatch-curator-failopen`, `prefetch-content-split`, `subquery-fanout-normalization`, `mcp-strategy-cache`, `session-scoped-mcp-wiring`, `visited-url-dedup-contract`: one question fans into parallel sub-queries across the right data plane without double-paying MCP, re-scraping prefetched pages, or re-visiting URLs.
- **Context compression** — `compression-fast-path-thresholds`, `retriever-content-cap`: cheap inputs stay uncompressed; big ones survive embedding limits.
- **Scraping & throttling** — `browse-image-dedup-contract`, `scraper-routing-dedupe`, `global-rate-limiter-singleton`: right backend per URL, honest side-effect registration, one global politeness budget.
- **Deep research** — `deep-research-descent-budget`, `context-word-budget-fold`, `empty-descent-unbound-bug`: bounded recursion whose early-return path is a known latent crash.
- **Parsing & report** — `json-rescue-grammars`, `writer-abstention-gate`, `report-prompt-ladder-collapse-retry`, `auxiliary-write-failopen-empty`, `subtopics-fallback-shape-asymmetry`, `detailed-report-subtopic-loop`, `deterministic-references`: malformed LLM output repaired greedily, nothing written from nothing, auxiliary sections fail open to empty, multi-subtopic hosts dedup by shared URL set + two-sided content guards, byte-stable bibliographies.
- **Registry & providers** — `retriever-resolution-chain`, `embedding-provider-match-table`, `mcp-tool-selection-fallback`, `mcp-result-shape-normalizer`: swappable engines behind strict shapes with degrade-not-crash fallbacks.

## Extending the foundation
Add one source-confirmed capsule-v2 per porting question: loader line here, matching map entry above, decisive excerpt + invariant + executed probe + `search_graph` Retrieve against `gpt-researcher` (new capsules carry the canonical Retrieve block; pre-pass-2 capsules cite probes from the pass-1 scratch battery instead — upgrade opportunistically on touch). Candidate next seams live in `backend/server` (websocket lifecycle + BasicReport), the `scraper/*` family interiors (nodriver rate-limit ladder, firecrawl auto-pip, tavily_extract), `mcp/tool_selector.py` LLM arm beyond the fallback capsule, and `config/config.py` defaults/validation twins; `multi_agents/` (LangGraph editor/publisher loop) and `frontend/nextjs` only on a product question.

## Provenance
gpt-researcher (assafelovic), Apache-2.0 license, `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8` (= base_sha, checkout HEAD verified); Codebase Memory project `gpt-researcher` (5,699n / 15,949e FULL mode, generation 2026-08-26T01:42:19Z, head==base==pin zero drift; parse_partial ×3 = two Dockerfiles + nginx conf, none cited). Pass 1 (2026-08-23) mined 22 capsule-v2 under the since-retired twin project name `ext-gpt-researcher`; pass 2 (2026-08-26, FAC-199 dedicated lane) re-indexed the canonical short-name project, revalidated 27 cited paths live (`no_recorded_issue`/`metadata_match`), repaired the dead project citations fleet-wide, and added 5 new capsules for genuinely uncited conductor/orchestration seams; pass 3 (2026-08-27, bounded deep-learning pass) added 4 writing/host-plane capsules (report prompt ladder + collapse retry, auxiliary fail-open contract, subtopics fallback shape asymmetry, DetailedReport subtopic loop) under the same pin — Codebase Memory MCP was not connected that session, so evidence is direct source+test reading recorded in the work record. Gate-5: upstream pytest suites pin parsing/dedup/thresholds but need live API keys AND aiofiles+deps absent in-lane (executed collection ERROR recorded) — deterministic byte-anchor battery per capsule; pass-1's `scratch-gptr-pass1/probe_battery.py` evidence retained on legacy capsules.

## Full view (memory graph)
Revalidate `gpt-researcher` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`; source decides shipped claims. Graph hot seams resolve line-exact via BM25 `search_graph` (e.g. `create_chat_completion` → utils/llm.py:41-152; `trim_context_to_word_limit` → skills/deep_research.py:213-231; `_normalize_sub_queries` → actions/query_processing.py:6-34). Semantic mode scores low (<0.06) on this graph — BM25 symbol queries are the working primitive. Layers: `agent.py` is the hub fanning into five skill components (`research_conductor`, `report_generator`, `context_manager`, `scraper_manager`, `source_curator`) constructed in `__init__`; inbound drivers are backend/server websocket Researcher, backend report types, cli.main, LangGraph multi_agents, evals; TESTS edges concentrate on retrievers and parsing helpers.

## Boundaries
Adopt the pure contracts: normalization/fallback ladders, cost ladders, word-budget fold, rate-limit singleton shape, JSON rescue grammar, sorted-reference determinism, result-shape normalizers. Adapt integration specifics: LangChain compressor/retriever classes, provider constructor tables (prices/models drift), websocket streaming envelope, FastAPI backend routes. Omit product behavior: `frontend/nextjs` UI, `docs/`, deployment terraform/docker topologies, eval harnesses — and do NOT rely on the deep-research zero-query path returning cleanly (known UnboundLocalError, see capsule).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`auxiliary-write-failopen-empty.md`](./auxiliary-write-failopen-empty.md)
- [`browse-image-dedup-contract.md`](./browse-image-dedup-contract.md)
- [`compression-fast-path-thresholds.md`](./compression-fast-path-thresholds.md)
- [`conduct-image-pregeneration-ladder.md`](./conduct-image-pregeneration-ladder.md)
- [`context-word-budget-fold.md`](./context-word-budget-fold.md)
- [`deep-research-descent-budget.md`](./deep-research-descent-budget.md)
- [`detailed-report-subtopic-loop.md`](./detailed-report-subtopic-loop.md)
- [`deterministic-references.md`](./deterministic-references.md)
- [`embedding-provider-match-table.md`](./embedding-provider-match-table.md)
- [`empty-descent-unbound-bug.md`](./empty-descent-unbound-bug.md)
- [`global-rate-limiter-singleton.md`](./global-rate-limiter-singleton.md)
- [`json-rescue-grammars.md`](./json-rescue-grammars.md)
- [`llm-retry-temperature-ladder.md`](./llm-retry-temperature-ladder.md)
- [`mcp-result-shape-normalizer.md`](./mcp-result-shape-normalizer.md)
- [`mcp-strategy-cache.md`](./mcp-strategy-cache.md)
- [`mcp-tool-selection-fallback.md`](./mcp-tool-selection-fallback.md)
- [`prefetch-content-split.md`](./prefetch-content-split.md)
- [`provider-model-policy-tables.md`](./provider-model-policy-tables.md)
- [`quick-search-multi-retriever-merge.md`](./quick-search-multi-retriever-merge.md)
- [`report-prompt-ladder-collapse-retry.md`](./report-prompt-ladder-collapse-retry.md)
- [`report-source-dispatch-curator-failopen.md`](./report-source-dispatch-curator-failopen.md)
- [`retriever-content-cap.md`](./retriever-content-cap.md)
- [`retriever-resolution-chain.md`](./retriever-resolution-chain.md)
- [`scraper-routing-dedupe.md`](./scraper-routing-dedupe.md)
- [`session-scoped-mcp-wiring.md`](./session-scoped-mcp-wiring.md)
- [`step-attributed-cost-ledger.md`](./step-attributed-cost-ledger.md)
- [`subquery-fanout-normalization.md`](./subquery-fanout-normalization.md)
- [`subtopics-fallback-shape-asymmetry.md`](./subtopics-fallback-shape-asymmetry.md)
- [`usage-first-cost-ladder.md`](./usage-first-cost-ladder.md)
- [`visited-url-dedup-contract.md`](./visited-url-dedup-contract.md)
- [`writer-abstention-gate.md`](./writer-abstention-gate.md)
