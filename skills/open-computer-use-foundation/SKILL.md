---
name: open-computer-use-foundation
description: "Use when porting minimal computer-use agent loops: sandbox tool dispatch, grounding clicks, multi-provider LLM shims, and keep-alive streaming."
metadata:
  hermes:
    tags: [computer-use, agents, llm-providers, grounding, e2b, foundations]
    category: autonomous-ai-agents
disable-model-invocation: true
---
# open-computer-use: Minimal computer-use agent foundation

## Use this for
Use when building or porting an agent that drives a real computer (screenshots, mouse, keyboard, shell) through LLM tool calls — especially pairing a vision grounder with a separate action model across multiple LLM vendors. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/tool-registry-guarded-dispatch.md` — how tools get declared and safely invoked without hard-wiring?
- `references/thought-action-loop.md` — what is the exact turn order, and which messages enter history vs only the transcript?
- `references/vision-thought-prompt-contract.md` — how does the agent decide the objective is complete without a completion tool call?
- `references/grounding-click-funnel.md` — how does a natural-language click target become verified pixel coordinates?
- `references/tool-call-salvage.md` — what happens when a provider returns a function call as plain text?
- `references/image-block-ladder.md` — how do raw screenshot bytes become provider-correct image content blocks?
- `references/provider-alias-classes.md` — how are 10+ vendors onboarded without touching the core loop?
- `references/mistral-prefix-shim.md` — how does an assistant-prefix message become a single user turn?
- `references/anthropic-system-extraction.md` — what differs in calling Anthropic beyond the image block?
- `references/sandbox-stream-lifecycle.md` — how does a long agent session survive sandbox timeout, and how is the display streamed?
- `references/logger-as-value.md` — how do log lines become message content without a second append?
- `references/grounding-provider-spi.md` — how do two vision grounder models with different output grammars share one call site?
- `references/mock-sandbox-contract.md` — how is the whole agent exercised without E2B or live models?
- `references/browser-process-isolation.md` — why does a VNC window need a separate OS process?

## Capsule map
- **Tool system** — `tool-registry-guarded-dispatch`: registry-gated getattr + exception→string dispatcher keeps the loop alive on any failure.
- **Agent loop** — `thought-action-loop`: four-slot turn shape (objective/thought/tool-call/observation) with text-only memory and per-turn sandbox keep-alive.
- **Agent loop** — `vision-thought-prompt-contract`: prompt-only describe→verdict→next-step grammar lets a cheap vision model gate completion.
- **Grounding** — `grounding-click-funnel`: same-call screenshot→bbox→midpoint→debug-dot→move→click ladder kills coordinate staleness.
- **Grounding** — `grounding-provider-spi`: one-method duck-typed SPI with vendor-owned parsing (OS-Atlas token stream vs ShowUI normalized pair).
- **LLM providers** — `tool-call-salvage`: native-first + greedy-brace text fallback recovers under-parsed function calls.
- **LLM providers** — `image-block-ladder`: bytes-in-content convention re-wrapped per provider (data-URL sniff vs hardcoded png base64).
- **LLM providers** — `provider-alias-classes`: subclass-as-config vendor onboarding with alias resolution at construction.
- **LLM providers** — `mistral-prefix-shim`: destructive merge of trailing assistant turns satisfies continuation-style APIs.
- **LLM providers** — `anthropic-system-extraction`: system-role hoisting + canonical tool-call normalization + mandatory max_tokens.
- **Runtime** — `sandbox-stream-lifecycle`: set_timeout-before-inference keep-alive plus in-sandbox ffmpeg listen server and group-kill teardown.
- **Runtime** — `logger-as-value`: log() returns its input so console, HTML transcript, and message content stay identical by construction.
- **Testing** — `mock-sandbox-contract`: MockSandbox pins the four-verb sandbox portability surface.
- **UI** — `browser-process-isolation`: pywebview in its own OS process with queue-sentinel close keeps asyncio free.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
open-computer-use (Apache-2.0), `master@610bac85`; Codebase Memory project `ext-open-computer-use` (FULL index, 206 nodes / 651 edges, generation matches HEAD `610bac85`, parse_partial ×0, not_indexed = 3 PNG assets by design).

## Full view (memory graph)
Revalidate `ext-open-computer-use` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: registry dispatch, turn shape, salvage ladder, image-block wrapping, grounding funnel, mock contract. Adapt host-specific integrations: E2B desktop sandbox verbs, gradio Space endpoints, pywebview viewer, ffmpeg flags. Omit product behavior: main.py CLI entrypoint, HTML log template cosmetics, the disabled DisplayClient recording path.
