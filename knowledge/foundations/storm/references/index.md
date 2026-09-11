<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# storm (Stanford STORM): Grounded Article Generation Foundation

## Use this for
Use when building or porting systems that write cited, Wikipedia-like articles from web evidence: perspective-guided information-seeking conversations, outline-then-section generation with per-section retrieval, inline `[n]` citation sanitization and renumbering, URL-unified bibliographies, swappable search-engine adapters, litellm-backed provider wrappers with two-layer caching and per-stage usage ledgers, and Co-STORM's hierarchical knowledge-base mind map. Source code is ground truth; each capsule carries a decisive excerpt, invariant, executed probe, and graph retrieval.

## Load the matching source dump
### Provider & serving plane (`lm.py`)
- `./dual-layer-lm-cache.md` — LRU-over-litellm-disk cache keyed on the serialized request JSON; env-default cost-map and drop_params wiring.
- `./text-completion-provider-degradation.md` — serving chat configs through completions endpoints via provider-prefix rewrite and messages flattening.
- `./usage-ledger-reset-protocol.md` — `_lm`/`rm` naming convention + get-and-reset drain so every stage's token/query cost lands once.
### Citation grounding plane (`utils.py`, dataclasses)
- `./two-phase-citation-renumbering.md` — placeholder-moat remapping of `[old]→[new]` without collisions; the latent no-op twins to avoid.
- `./url-unified-reference-merge.md` — per-section local numbers folded into one URL-keyed bibliography, then reordered by first appearance.
- `./grounded-answer-citation-sanitizer.md` — group-split → dedupe → last-sentence truncation → over-range strip ladder that keeps `[n]` honest.
- `./information-identity-citation-ledger.md` — md5 identity over (url, sorted snippets, meta) and hash→uuid mint-once under lock.
### Outline & article assembly plane
- `./outline-grammar-coercion.md` — topic reset, bullet→heading promotion, twelve tail-section amputations before tree parsing.
- `./article-tree-markdown-parser.md` — `(node, level)` stack ingestion of flat markdown into nested section dicts.
- `./section-skip-heuristics.md` — skip intro/conclusion/summary sections; write the lead LAST from the finished draft.
- `./word-budget-line-preserving-truncation.md` — word-cap context clamping that never emits a partial line.
### Retrieval plane (`rm.py`, `storm_dataclass.py`)
- `./retriever-adapter-contract.md` — uniform four-key dict contract, usage counters, skip-on-error loops, and the exclude_urls dummy traps.
- `./snippet-retrieval-dedup.md` — flat parallel arrays + ascending-argsort top-k slice + clone-before-narrow retrieval.
- `./parallel-embedding-order-restore.md` — concurrent embedding fan-out with sort-back-to-input-order.
### Orchestration plane (`engine.py`, curation)
- `./runner-resume-from-artifacts.md` — four-stage pipeline where every stage loads its predecessor's artifacts on skip.
- `./persona-conversation-simulation.md` — sentinel termination, sliding-window dialogue context, always-first default persona, ground-truth exclusion.
- `./wiki-toc-persona-induction.md` — fail-soft persona induction from related Wikipedia TOCs; stack-derived heading indentation; numbered-line output grammar.
- `./outline-draft-then-refine.md` — topic-only draft outline + unconditional conversation-guided refinement; dialogue denoising; old-outline-as-OutputField prompt trick.
- `./knowledge-base-mindmap-lifecycle.md` — clean→expand→clean→relabel reorganization of the Co-STORM mind map.
- `./hierarchical-event-logging.md` — stage buckets + event stacks + drain-on-close usage attribution.
### Co-STORM discourse plane (`collaborative_storm/`)
- `./costorm-turn-policy-ladder.md` — who-speaks-next priority chain with one-shot moderator latch, dry-run-safe rotation, and answer-domination trigger.
- `./expert-action-grammar-parse.md` — four-label contribution grammar with bracketed parse fallback, fail-loud Undefined, and the load-bearing `resposne` typo pair.
- `./moderator-novelty-snippet-scoring.md` — identity-hash unused-snippet exclusion + claim-gated dissimilarity scoring + round-robin cross-turn merge.
- `./grounded-ask-module-contract.md` — decompose→retrieve→budget-format→refuse-by-default→sanitize→rebind lifecycle of one cited conversational answer.
- `./warmstart-mini-storm.md` — background research → perspectives → outline-first KB seed → synthesized catch-up transcript, under lock and swallow-isolation rules.
- `./mindmap-intent-placement.md` — embedding-ranked candidate choice then layer-by-layer LM navigation; frozen-snapshot parallel vs mutating sequential inserts.
### Guardrails plane
- `./input-appropriateness-gate.md` — length → charset → small-model verdict gate that fails closed.

## Capsule map
- **Provider & serving** — `dual-layer-lm-cache`, `text-completion-provider-degradation`, `usage-ledger-reset-protocol`: cheap repeat calls, legacy-endpoint support, honest per-stage accounting.
- **Citation grounding** — `two-phase-citation-renumbering`, `url-unified-reference-merge`, `grounded-answer-citation-sanitizer`, `information-identity-citation-ledger`: every `[n]` traces to a deduplicated source through collision-safe rewrites.
- **Outline & assembly** — `outline-grammar-coercion`, `article-tree-markdown-parser`, `section-skip-heuristics`, `word-budget-line-preserving-truncation`: free-form LLM output coerced into strict trees under line-preserving budgets.
- **Retrieval** — `retriever-adapter-contract`, `snippet-retrieval-dedup`, `parallel-embedding-order-restore`: swappable engines behind one dict shape with order-safe embeddings.
- **Orchestration** — `runner-resume-from-artifacts`, `persona-conversation-simulation`, `wiki-toc-persona-induction`, `outline-draft-then-refine`, `knowledge-base-mindmap-lifecycle`, `hierarchical-event-logging`: resumable stages, terminating dialogues, web-evidence persona induction, two-stage outline refinement, self-cleaning mind maps, attributable logging.
- **Co-STORM discourse** — `costorm-turn-policy-ladder`, `expert-action-grammar-parse`, `moderator-novelty-snippet-scoring`, `grounded-ask-module-contract`, `warmstart-mini-storm`, `mindmap-intent-placement`: flag-spec turn taking, constrained contribution labels, novelty-gated perspective injection, per-turn cited answering, hot-start choreography, and two-stage mind-map placement.
- **Guardrails** — `input-appropriateness-gate`: fail-closed admission before spending research budget.

## Extending the foundation
Add one source-confirmed capsule-v2 per porting question: loader line here, matching map entry above, decisive excerpt + invariant + executed probe + `search_graph` Retrieve against `storm`. Candidate next seams live in `collaborative_storm/` (expert utterance generation, grounded question asking, knowledge-base summary modules).

## Provenance
storm (stanford-oval), MIT license, `main@fb951af7744dab086e34962e9bc6fe878e145f83` (= base_sha, unchanged since index; checkout HEAD verified identical, tree clean); Codebase Memory project `storm` (902n / 3,904e FULL mode, generation 2026-08-25T20:09:07Z, generation_matches, zero parse_partial/skipped; only 7 image assets excluded by design). Pass-1 squeeze mined 19 capsules against the then-live graph project `ext-storm` [DONE:274]. Pass-2 (FAC-267) repaired the fleet after that project vanished from the registry: fresh FULL re-index under `storm` at the same pin, 21 dead-project citations replaced across SKILL.md + all pass-1 capsules, +2 new capsule-v2 (`wiki-toc-persona-induction`, `outline-draft-then-refine`). No upstream test suite exists — probes are deterministic source/graph checks plus AST-lifted executions recorded by each capsule, not runner passes.

## Full view (memory graph)
Revalidate `storm` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`; source decides shipped claims. Graph entry points: `examples.*.main` composition roots (12); hot seams: `STORMWikiRunner.post_run`, `STORMWikiLMConfigs.set_question_asker_lm`, `WebPageHelper.__init__`, `LoggingWrapper.log_event` (fan-in 13). Layers: `dataclass`/`rm`/`utils`/`logging_wrapper` are pure fan-in cores; `storm_wiki` is the hub (100 inbound / 51 outbound). Five-role LM config slots (`conv_simulator_lm`, `question_asker_lm`, `outline_gen_lm`, `article_gen_lm`, `article_polish_lm`) are the quality/cost tuning surface.

## Boundaries
Adopt the pure contracts: citation ladders, placeholder renumbering, identity/hash ledger, stack parsers, truncation algorithm, adapter dict shape. Adapt integration specifics: dspy module/signature plumbing, litellm global config, sentence-transformer encoder choice, Qdrant vector-store bootstrap. Omit product behavior: Streamlit demo frontend (`frontend/demo_light/`), example scripts, deprecated pre-v1.1 dspy wrapper classes (`OpenAIModel`, `DeepSeekModel`, `GroqModel`, `ClaudeModel`, `VLLMClient`, `OllamaClient`, `TGIClient`, `TogetherClient`, `GoogleModel`) except as ledger-contract references, and the Co-STORM conversational engine internals beyond the mined mind-map lifecycle.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`article-tree-markdown-parser.md`](./article-tree-markdown-parser.md)
- [`costorm-turn-policy-ladder.md`](./costorm-turn-policy-ladder.md)
- [`dual-layer-lm-cache.md`](./dual-layer-lm-cache.md)
- [`expert-action-grammar-parse.md`](./expert-action-grammar-parse.md)
- [`grounded-answer-citation-sanitizer.md`](./grounded-answer-citation-sanitizer.md)
- [`grounded-ask-module-contract.md`](./grounded-ask-module-contract.md)
- [`hierarchical-event-logging.md`](./hierarchical-event-logging.md)
- [`information-identity-citation-ledger.md`](./information-identity-citation-ledger.md)
- [`input-appropriateness-gate.md`](./input-appropriateness-gate.md)
- [`knowledge-base-mindmap-lifecycle.md`](./knowledge-base-mindmap-lifecycle.md)
- [`mindmap-intent-placement.md`](./mindmap-intent-placement.md)
- [`moderator-novelty-snippet-scoring.md`](./moderator-novelty-snippet-scoring.md)
- [`outline-draft-then-refine.md`](./outline-draft-then-refine.md)
- [`outline-grammar-coercion.md`](./outline-grammar-coercion.md)
- [`parallel-embedding-order-restore.md`](./parallel-embedding-order-restore.md)
- [`persona-conversation-simulation.md`](./persona-conversation-simulation.md)
- [`retriever-adapter-contract.md`](./retriever-adapter-contract.md)
- [`runner-resume-from-artifacts.md`](./runner-resume-from-artifacts.md)
- [`section-skip-heuristics.md`](./section-skip-heuristics.md)
- [`snippet-retrieval-dedup.md`](./snippet-retrieval-dedup.md)
- [`text-completion-provider-degradation.md`](./text-completion-provider-degradation.md)
- [`two-phase-citation-renumbering.md`](./two-phase-citation-renumbering.md)
- [`url-unified-reference-merge.md`](./url-unified-reference-merge.md)
- [`usage-ledger-reset-protocol.md`](./usage-ledger-reset-protocol.md)
- [`warmstart-mini-storm.md`](./warmstart-mini-storm.md)
- [`wiki-toc-persona-induction.md`](./wiki-toc-persona-induction.md)
- [`word-budget-line-preserving-truncation.md`](./word-budget-line-preserving-truncation.md)
