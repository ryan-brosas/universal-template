<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Ollama: local model server foundation

## Use this for
Use when building or porting a local LLM inference server: model lifecycle (load, reuse, evict, unload), memory-aware scheduling, prompt rendering/parsing pipelines, streamed response codecs, or OpenAI/Anthropic-compatible facades. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./scheduler-two-loop-core.md` — how does one model load at a time while loaded models serve in parallel?
- `./scheduler-model-key.md` — what identity keys the loaded-runner map when some models have no file path?
- `./scheduler-oom-retry-ladder.md` — how do loads/generations recover from OOM without infinite retry?
- `./scheduler-gpu-placement.md` — which GPUs host a new runner (explicit pin → single fit → best group)?
- `./scheduler-auto-numbatch.md` — how is generation batch auto-sized with a VRAM surcharge fed back into prediction?
- `./scheduler-vram-recovery-eviction.md` — when is it safe to load after an unload, and who gets evicted?
- `./scheduler-needs-reload.md` — when must a loaded runner reload vs serve (auto-value reconciliation)?
- `./chat-dual-execution-modes.md` — native llama-server templating vs Ollama-rendered chat, and the coupled launch flag?
- `./chat-structured-outputs-double-request.md` — grammar-constrained JSON without corrupting thinking output?
- `./thinking-stream-parser.md` — five-state `<think>` splitter that never re-emits across chunk boundaries.
- `./harmony-parser-frames.md` — gpt-oss channel frames, prefill seeding, TS-identifier tool-name mapping.
- `./tools-template-tag-parser.md` — tool-call delimiter inferred from the chat template + escape-aware JSON scanning.
- `./builtin-parser-registry.md` — the five-method Parser contract plugging ~20 per-model grammars into one completion loop.
- `./openai-chat-streaming-codec.md` — internal NDJSON → spec-exact SSE chunks (mixed split, pinned created, finish+usage+DONE).
- `./anthropic-messages-bridge.md` — /v1/messages shim: convert→re-encode-body→reuse handler, relax_thinking, effort mapping.
- `./inference-model-cache.md` — digest-validated singleflight model cache returning deep clones.
- `./model-capability-ladder.md` — where completion/tools/vision/thinking capabilities come from (config→gguf→template→parser→family→filters).
- `./chat-prompt-truncation.md` — render-tokenize truncation preserving system messages and the last message.
- `./model-ref-routing.md` — `model:tag:cloud` suffix routing to local, remote-proxy, or cloud execution.
- `./renderer-registry-bos.md` — per-family renderer registry coupled to LeadingBOS selection.
- `./parallel-contextshift-overrides.md` — per-family numParallel clamps and deepseek2 context-shift prohibition.
- `./mmap-defaults-host-pressure.md` — reason-coded mmap overrides including the fits-in-VRAM guard.
- `./ndjson-stream-contract.md` — the typed-channel wire contract every compat codec consumes.

## Capsule map
- **Scheduling kernel** — `scheduler-two-loop-core`: pending/completed goroutine pair; single-loader serialization, refCount+expireTimer lifecycle, non-blocking admission (`ErrMaxQueue`).
- **Runner identity** — `scheduler-model-key`: ModelPath → `digest:` prefix → Name fallback ladder shared by all scheduler sites.
- **OOM recovery** — `scheduler-oom-retry-ladder`: predict-evict preflight (80% headroom) → one-shot auto ctx/batch reduce → evict-all-and-retry with latch → runtime idle-expiry.
- **GPU placement** — `scheduler-gpu-placement`: library-partitioned groups; explicit main_gpu pin; ≤80% single-device fit else best group; iGPU clamped by system RAM.
- **Batch sizing** — `scheduler-auto-numbatch`: 512/1024/2048 context tiers walking down under headroom gates; surcharge (768 MiB/2 GiB) included in predictions.
- **VRAM convergence** — `scheduler-vram-recovery-eviction`: baseline-before-unload, 75%-recovery-or-5s poll, idle-first victim via duration+name sort, pid-mismatch orphan cleanup.
- **Reload decision** — `scheduler-needs-reload`: clamp effective ctx, normalize auto-vs-auto values, then DeepEqual adapters/projectors/options + ping (10s/2min while loading).
- **Chat mode duality** — `chat-dual-execution-modes`: one predicate picks Rendered vs Native AND sets DisableJinja at launch; DebugRenderOnly dumps the exact prompt.
- **Structured outputs** — `chat-structured-outputs-double-request`: generate-free→cancel-on-content→replay-with-grammar carrying thinking as assistant history; narrow self-cancel swallow.
- **Thinking parser** — `thinking-stream-parser`: LookingForOpening→…→ThinkingDone states; suffix-overlap buffering; untrimmed passthrough on tag-skip.
- **Harmony frames** — `harmony-parser-frames`: start/header/message-end event stream; assistant-prefill channel resume; lossy tool rename with mandatory reverse map; preserved tokens minus EOG.
- **Tool tag parser** — `tools-template-tag-parser`: `{{if .ToolCalls}}` text node yields the tag; brace-mode first-char gate; longest-name suffix hold; escape-aware brace scanner.
- **Parser registry** — `builtin-parser-registry`: Init/Add(done)/PreservedTokens/Has* contract; parse errors cancel upstream and emit one error frame instead of wedging.
- **OpenAI SSE codec** — `openai-chat-streaming-codec`: mixed-response two-chunk split, per-stream created pin, empty-trailer suppression, finish chunk + optional usage chunk + `[DONE]`, stop→tool_calls remap only.
- **Anthropic bridge** — `anthropic-messages-bridge`: total conversion before handler reuse; relax_thinking for claude-code; effort xhigh→high; built-in web_search wins name collisions; usage rebasing across search loops.
- **Model cache** — `inference-model-cache`: live-manifest digest validation, singleflight dedupe, enumerated deep clone so handlers can mutate safely.
- **Capability ladder** — `model-capability-ladder`: fixed-order source union ending in suppression filters; template preference by tool round-trip fidelity.
- **Prompt truncation** — `chat-prompt-truncation`: advance front pointer, re-render+tokenize each window, salvage dropped-prefix systems, never drop last message; 768-token/image estimate.
- **Ref routing** — `model-ref-routing`: `:cloud` suffix proxy, remote-manifest reverse proxy with allowlist + option defaults merge + identity rewrite per chunk.
- **Renderer registry** — `renderer-registry-bos`: constructor registry with variant struct fields; BOS from the same resolver as rendering.
- **Family overrides** — `parallel-contextshift-overrides`: embedding models parallel=1; eleven unsafe families forced serial before VRAM math; deepseek2 forbids context shift.
- **mmap policy** — `mmap-defaults-host-pressure`: cpu/windows_cuda/metal_partial reasons plus RAM-pressure disable guarded by fits-in-VRAM check.
- **Wire contract** — `ndjson-stream-contract`: typed error frames; pre-stream real status vs mid-stream terminal frame; non-stream aggregation of thinking/content/tools/logprobs.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Ollama (MIT), `main@fb30760996871fa9460115c753afd2c60d4ab0f7` (2026-08-21); Codebase Memory project `ext-ollama` (root `/mnt/hdd/utopia/inspo/external/ollama`, branch main, FULL index, 153,806 nodes / 330,464 edges, generated 2026-08-23T09:10:40Z, generation_matches=true; freshness proven post-drift by resolving drift-introduced symbols `newModelRecommendationsCache`; parse_partial limited to docs/proto/jinja assets, none cited).

## Full view (memory graph)
Revalidate `ext-ollama` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Coverage sweep on all 15 cited paths returned no_recorded_issue + metadata_match. BM25 search_graph resolves Function/Method/Struct nodes; doc-shaped Section nodes are absent but irrelevant here. Direct tests decide shipped claims: `go test ./thinking/ ./harmony/ ./tools/ ./server/ -run 'TestSched|TestInferenceModelCache|TestThinkingStreaming' ./middleware/ ./openai/ ./model/parsers/ ./model/renderers/` all PASS at the pinned commit.

## Boundaries
Adopt the scheduler loop shape, memory-prediction ladders, parser interfaces, and streaming codec contracts — they are engine-agnostic. Adapt thresholds (80% headroom, batch tiers, 5s VRAM wait, 768 tokens/image) and family lists to your hardware/runtime matrix. Omit llama-server subprocess management, MLX runner branches, cloud/remote federation specifics, and the app/desktop surface — those are transport and product layers outside this foundation's contracts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`anthropic-messages-bridge.md`](./anthropic-messages-bridge.md)
- [`builtin-parser-registry.md`](./builtin-parser-registry.md)
- [`chat-dual-execution-modes.md`](./chat-dual-execution-modes.md)
- [`chat-prompt-truncation.md`](./chat-prompt-truncation.md)
- [`chat-structured-outputs-double-request.md`](./chat-structured-outputs-double-request.md)
- [`harmony-parser-frames.md`](./harmony-parser-frames.md)
- [`inference-model-cache.md`](./inference-model-cache.md)
- [`mmap-defaults-host-pressure.md`](./mmap-defaults-host-pressure.md)
- [`model-capability-ladder.md`](./model-capability-ladder.md)
- [`model-ref-routing.md`](./model-ref-routing.md)
- [`ndjson-stream-contract.md`](./ndjson-stream-contract.md)
- [`openai-chat-streaming-codec.md`](./openai-chat-streaming-codec.md)
- [`parallel-contextshift-overrides.md`](./parallel-contextshift-overrides.md)
- [`renderer-registry-bos.md`](./renderer-registry-bos.md)
- [`scheduler-auto-numbatch.md`](./scheduler-auto-numbatch.md)
- [`scheduler-gpu-placement.md`](./scheduler-gpu-placement.md)
- [`scheduler-model-key.md`](./scheduler-model-key.md)
- [`scheduler-needs-reload.md`](./scheduler-needs-reload.md)
- [`scheduler-oom-retry-ladder.md`](./scheduler-oom-retry-ladder.md)
- [`scheduler-two-loop-core.md`](./scheduler-two-loop-core.md)
- [`scheduler-vram-recovery-eviction.md`](./scheduler-vram-recovery-eviction.md)
- [`thinking-stream-parser.md`](./thinking-stream-parser.md)
- [`tools-template-tag-parser.md`](./tools-template-tag-parser.md)
