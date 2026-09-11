<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# paper-qa: Citation-Grounded RAG Foundation

## Use this for
Use when building or porting systems that answer questions with verifiable citations: LLM-output JSON salvage, evidence-context scoring pipelines, scholarly-metadata provider ladders (Crossref/S2/OpenAlex), bibtex→citation rendering, `pqac-*` keyed in-text citations with derived bibliographies, tantivy-backed paper search indexes, and agent tool loops over shared document state. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./llm-json-salvage-ladder.md` — ordered repair ladder that parses near-JSON LLM output without corrupting valid JSON.
- `./evidence-context-retry-taxonomy.md` — which context failures retry once vs abandon, with cost results always preserved.
- `./citation-strip-score-ladder.md` — regex removal of author-year citations + 0-10 relevance score extraction fallbacks.
- `./pqac-context-id-grammar.md` — stable 8-hex context ids (`md5(question+context[:500])[:8]`) powering citations and dedupe.
- `./answer-bibliography-assembly.md` — raw-answer parentheticals rewritten to deduped docnames; hallucinated keys swept; numbered References derived only from resolvable ids.
- `./docdetails-merge-algebra.md` — per-field precedence when summing conflicting provider metadata.
- `./docdetails-validator-chain.md` — the ordered DOI-normalize → bibtex-generate → overwrite-gate pipeline every DocDetails passes.
- `./metadata-client-ladder.md` — provider waves with hydration-based early stop and swallow-to-None degradation.
- `./provider-title-match-gate.md` — local Jaccard + exact-DOI echo acceptance instead of trusting API rank.
- `./bibtex-formatting-ladder.md` — type-table cleaning, Person-aware author injection, deterministic key rewrite.
- `./docs-ingestion-gate.md` — aadd end-to-end: peek-citation, structured extract, upgrade, validity, idempotent dockey add.
- `./chunking-dispatcher.md` — extension-dispatched parsers/chunkers; page-span chunk names as load-bearing metadata.
- `./mmr-vector-search.md` — vectorized MMR (λ≥1 disables), partition interleaving, Qdrant twin id determinism.
- `./tantivy-index-lock-plane.md` — LockBusy retry ladder + refcounted Index-open cache for concurrent indexers.
- `./agent-tool-loop-status.md` — per-tool CONCURRENCY_SAFE flags, string status protocol, search-offset cursors.
- `./context-serializer-cannot-answer.md` — sort-cap-filter context assembly + template-derived refusal sentinel.
- `./media-enrichment-filter.md` — pre-chunk image/table captioning with RELEVANT/IRRELEVANT fail-open label protocol.
- `./settings-identity-factories.md` — strategy-encoded index names, session config md5, single-entry LiteLLM router defaults.
- `./docname-text-validity-plumbing.md` — citation→docname token ladder traps + entropy text-validity gates.
- `./directory-index-manifest-grammar.md` — CSV manifest fail-open read + strict DocDetails row validation; dual absolute/relative key lookup.
- `./directory-index-sync-rebuild.md` — indexed-vs-directory set diff, filename-keyed skip, sync-remove vs warn, build=False rebuild guard.
- `./process-file-error-taxonomy.md` — ERROR-tombstone crash resume, swallow-list (ValueError/ImpossibleParsingError), cross-task batched saves.
- `./searchindex-query-semantics.md` — two-stage query sanitization, field subsets, offset cursors, post-filter min_score, blob hydration.
- `./answers-index-reuse-plane.md` — every completed run recorded into a persistent JSON answers index; index_search rehydration.
- `./agent-runner-ladder.md` — fake→aviary→ldp backend dispatch, prebuilt-index gate, timeout/fail status algebra with forced gen_answer.
- `./aquery-prompt-chain.md` — pre→context→answer→post chain with session-id correlation, stage tags, per-stage token accounting, empty-context refusal before the big call.
- `./evidence-fanout-merge-algebra.md` — retrieval gate, bounded concurrent evidence scoring, score>0 set-dedupe merge, failure-inclusive token ledger.
- `./evidence-context-build-contract.md` — summary-JSON key algebra (summary/relevance_score/question-pop/extras), table splice + multimodal message, embedding-dropping Context rebuild.
- `./gather-evidence-agent-tool.md` — finally-guarded sub-question swap, EmptyDocsError guard, per-question top-N projection, delta-count observation.
- `./grouped-context-rendering.md` — group-after-filter rendering by question tag, first-appearance order, global valid_keys across groups.
- `./answer-attempt-budget.md` — tool-history-derived gen_answer cap, record-before-validate steps, tri-state has_successful_answer on budget exhaustion.

## Capsule map
- **LLM output robustness** — `llm-json-salvage-ladder`, `citation-strip-score-ladder`, `evidence-context-retry-taxonomy`: parse whatever the model actually says, then retry-or-drop with honest cost accounting.
- **Citation keys & bibliography** — `pqac-context-id-grammar`, `answer-bibliography-assembly`, `context-serializer-cannot-answer`: ids derive from content, answers cite only resolvable ids, hallucinations are swept.
- **Metadata acquisition** — `metadata-client-ladder`, `provider-title-match-gate`, `docdetails-merge-algebra`, `docdetails-validator-chain`, `bibtex-formatting-ladder`: multi-provider waves, strict acceptance, principled merging, provenance-tagged bibtex.
- **Ingestion & retrieval** — `docs-ingestion-gate`, `chunking-dispatcher`, `mmr-vector-search`, `tantivy-index-lock-plane`: idempotent adds, reproducible chunk fingerprints, MMR/partition search, concurrent index safety.
- **Directory-index lifecycle** — `directory-index-manifest-grammar`, `directory-index-sync-rebuild`, `process-file-error-taxonomy`, `searchindex-query-semantics`: resumable keyword-index builds over a paper directory with trusted-manifest seeding and sanitized BM25 queries.
- **Agent orchestration** — `agent-tool-loop-status`, `agent-runner-ladder`, `answers-index-reuse-plane`, `gather-evidence-agent-tool`, `answer-attempt-budget`: tools share state under explicit concurrency flags; backends dispatch through a status-normalizing runner; finished runs become searchable corpus; sub-question gathering restores session state in finally; answer attempts are budgeted with tri-state success.
- **Evidence & answer loop** — `aquery-prompt-chain`, `evidence-fanout-merge-algebra`, `evidence-context-build-contract`, `grouped-context-rendering`: stage-tagged multi-call answer pipeline, bounded fan-out with dedupe merge, structured summary-JSON→Context contract, group-after-filter multi-question rendering.
- **Config & validity plumbing** — `settings-identity-factories`, `docname-text-validity-plumbing`, `media-enrichment-filter`: strategy-encoded identity, docname/entropy gates, labeled media enrichment.

## Extending the foundation
Add one `./<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
paper-qa (Future-House), Apache-2.0, `main@57e89f7223b0960d5ee5ea048c69e3c47e088572` (= base_sha, unchanged since index). Pass 1 mined under graph project `ext-paper-qa`; that project no longer exists, and pass 2 re-established the gate as Codebase Memory project `paper-qa` (FULL re-index of the same checkout: 2,163n / 7,851e, generation 2026-08-25T19:57:59Z, zero parse_partial/skipped; all cited paths no_recorded_issue + metadata_match). Pass-2 squeeze [DONE:241]: directory-index lifecycle + agent runner (6 new capsules). Pass-3 squeeze [DONE]: evidence→answer loop — aquery prompt chain, evidence fan-out/merge, context build contract, agent gather twin, grouped rendering, answer-attempt budget (6 new capsules; pin and counts unchanged at pass-3 start).

## Full view (memory graph)
Revalidate `paper-qa` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph entry points: `agents.main.agent_query`; hot seams: `core.map_fxn_summary` (inbound callers Docs.aget_evidence → gather_evidence/gen_answer/aquery), `docs.Docs.aquery` (sole caller GenerateAnswer.gen_answer), `types.DocDetails.__add__` (sum()-aggregated by DocMetadataClient), `agents.search.get_directory_index` (inbound build_index/agent_query/paper_search), `agents.search.process_file`, `agents.env.PaperQAEnvironment.step` (answer-attempt budget + record-before-validate). Coverage caveat: `src/paperqa/cli.py` is graph-silent (no nodes; coverage freshness "missing", re-checked pass 3) — read it directly before citing CLI internals. `gather_with_concurrency` is imported from the external `lmi` package and has no in-repo source of truth.

## Boundaries
Adopt pure contracts: JSON salvage ladder, id grammar, merge algebra, score/citation ladders, chunk naming. Adapt host-specific integration: provider HTTP layers (httpx_aiohttp), litellm router configs, aviary/lmi tool abstractions, pybtex rendering. Omit product behavior: clinical-trials domain source, ldp RL-agent shims, CLI/Rich presentation, Zenodo/OpenReview contrib helpers.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-runner-ladder.md`](./agent-runner-ladder.md)
- [`agent-tool-loop-status.md`](./agent-tool-loop-status.md)
- [`answer-attempt-budget.md`](./answer-attempt-budget.md)
- [`answer-bibliography-assembly.md`](./answer-bibliography-assembly.md)
- [`answers-index-reuse-plane.md`](./answers-index-reuse-plane.md)
- [`aquery-prompt-chain.md`](./aquery-prompt-chain.md)
- [`bibtex-formatting-ladder.md`](./bibtex-formatting-ladder.md)
- [`chunking-dispatcher.md`](./chunking-dispatcher.md)
- [`citation-strip-score-ladder.md`](./citation-strip-score-ladder.md)
- [`context-serializer-cannot-answer.md`](./context-serializer-cannot-answer.md)
- [`directory-index-manifest-grammar.md`](./directory-index-manifest-grammar.md)
- [`directory-index-sync-rebuild.md`](./directory-index-sync-rebuild.md)
- [`docdetails-merge-algebra.md`](./docdetails-merge-algebra.md)
- [`docdetails-validator-chain.md`](./docdetails-validator-chain.md)
- [`docname-text-validity-plumbing.md`](./docname-text-validity-plumbing.md)
- [`docs-ingestion-gate.md`](./docs-ingestion-gate.md)
- [`evidence-context-build-contract.md`](./evidence-context-build-contract.md)
- [`evidence-context-retry-taxonomy.md`](./evidence-context-retry-taxonomy.md)
- [`evidence-fanout-merge-algebra.md`](./evidence-fanout-merge-algebra.md)
- [`gather-evidence-agent-tool.md`](./gather-evidence-agent-tool.md)
- [`grouped-context-rendering.md`](./grouped-context-rendering.md)
- [`llm-json-salvage-ladder.md`](./llm-json-salvage-ladder.md)
- [`media-enrichment-filter.md`](./media-enrichment-filter.md)
- [`metadata-client-ladder.md`](./metadata-client-ladder.md)
- [`mmr-vector-search.md`](./mmr-vector-search.md)
- [`pqac-context-id-grammar.md`](./pqac-context-id-grammar.md)
- [`process-file-error-taxonomy.md`](./process-file-error-taxonomy.md)
- [`provider-title-match-gate.md`](./provider-title-match-gate.md)
- [`searchindex-query-semantics.md`](./searchindex-query-semantics.md)
- [`settings-identity-factories.md`](./settings-identity-factories.md)
- [`tantivy-index-lock-plane.md`](./tantivy-index-lock-plane.md)
