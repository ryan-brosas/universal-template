---
name: agent-s-foundation
description: "Use when porting screenshot-driven computer-use agents — grounding-model coordinate generation, eval-based grounded-action execution, code-agent delegation with step budgets, behavior-narrator trajectory annotation, or Best-of-N comparative judging."
---
# Agent-S (gui_agents/s3): AgentS3 minimal GUI-agent loop foundations

## Use this for
Use when porting screenshot-driven computer-use agents: grounding-model coordinate generation, eval-based grounded-action execution, code-agent delegation with step budgets, behavior-narrator trajectory annotation, or Best-of-N comparative judging. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/agent-action-registry-reflection.md` — decorator-marked ACI methods become the worker's API docstring; reflection prompts appended at turn 0.
- `references/eval-grounded-action-funnel.md` — plan string → last fenced block → `eval()` against ACI → wait-on-failure fallback.
- `references/format-checker-reprompt-loop.md` — copied-messages reprompt loop with (success, feedback) checker pairs.
- `references/call-llm-safe-retry-ladder.md` — 3-attempt retry returning "" instead of raising; callers re-check emptiness.
- `references/dual-flush-strategy.md` — long-context models prune old images only; others pop whole turns; reflector history is all-user.
- `references/code-agent-handoff-contract.md` — `last_code_agent_result` mailbox consumed once by the worker's next prompt.
- `references/code-agent-budget-loop.md` — DONE/FAIL sentinels vs `BUDGET_EXHAUSTED_AFTER_N_STEPS`; empty response raises RuntimeError.
- `references/bash-python-result-dialects.md` — controller result shapes differ (`returncode` vs `return_code`); formatter keys off key presence.
- `references/thinking-tag-extraction.md` — `<thoughts>/<answer>` split tolerates missing tags; Anthropic thinking wrapped into tags.
- `references/provider-normalization-gate.md` — ollama/deepseek/qwen alias engines normalize base_url/api_key or raise; test-pinned.
- `references/engine-temperature-precedence.md` — instance temperature pins the value across providers; Azure cost accrual.
- `references/grounding-coordinate-resize.md` — raw digit regex from grounding model; rescale by grounding_width/height into screen space.
- `references/text-span-alignment-coords.md` — OCR word-id table + LLM span resolution; start/end alignment picks left edge vs right edge.
- `references/unicode-clipboard-type-path.md` — non-ASCII text routes through pyperclip paste, not pyautogui.write.
- `references/platform-action-dispatch.md` — switch/open emit per-OS pyautogui strings; linux uses wmctrl fuzzy-match script.
- `references/uno-set-cell-values-template.md` — spreadsheet writes as a self-contained UNO socket script template.
- `references/action-marker-annotation.md` — before-image markers parsed back out of emitted pyautogui strings; MoveTo→DragTo line state.
- `references/zoomed-after-annotation.md` — 300×300 crop around last mouse coord, Lanczos upscale + denoise, bounding box on full frame.
- `references/fact-caption-pipeline.md` — two-level semaphore parallel captioning with resume-by-file-existence.
- `references/variance-task-classification.md` — BoN scoring: constant vs variance tasks; actual score = minimum + judged gain.
- `references/local-env-controller-dialects.md` — minimal LocalController executes bash/python locally behind the same controller interface.
- `references/cli-dead-consent-gate.md` — defined-but-never-called permission dialog, `executor_plan` key mismatch, store_true-defaults-True flag.

## Capsule map
- **Worker spine** — `agent-action-registry-reflection`, `eval-grounded-action-funnel`, `format-checker-reprompt-loop`, `call-llm-safe-retry-ladder`, `dual-flush-strategy`: the AgentS3 hierarchy-free loop — one worker agent whose prompt documents itself from the ACI class, one action per turn, bounded context.
- **Code delegation** — `code-agent-handoff-contract`, `code-agent-budget-loop`, `bash-python-result-dialects`: GUI worker hands data-manipulation subtasks to a sandboxed code loop and reads back a structured report.
- **LLM plumbing** — `thinking-tag-extraction`, `provider-normalization-gate`, `engine-temperature-precedence`: tag parsing and provider-alias normalization shared by every agent role.
- **Grounding & actions** — `grounding-coordinate-resize`, `text-span-alignment-coords`, `unicode-clipboard-type-path`, `platform-action-dispatch`, `uno-set-cell-values-template`: description→pixel ladders and platform-specific action emitters.
- **Trajectory judging (BoN)** — `action-marker-annotation`, `zoomed-after-annotation`, `fact-caption-pipeline`, `variance-task-classification`: narrate what changed, then comparatively judge trajectories.
- **Local execution** — `local-env-controller-dialects`, `cli-dead-consent-gate`: the opt-in local runner and the consent gap around it.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Agent-S (MIT), `main@bffdb59c60cbbb38c3a190b2e91da12039e4063c`; Codebase Memory project `ext-agent-s` (1,255 nodes / 5,157 edges, ready, head==base zero drift, parse_partial ×1 requirements.txt none cited). Direct tests: `tests/test_providers.py` (5 tests, executed GREEN at pin under dep-stub shim for numpy/backoff/anthropic/openai).

## Full view (memory graph)
Revalidate `ext-agent-s` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: sibling generations s1/s2/s2_5 share symbol names (`OSWorldACI.click`, `flush_messages`) — route every Retrieve hit by the `s3.` path segment, not by rank alone.

## Boundaries
Adopt the pure contracts: decorator-to-docstring prompt assembly, eval-based grounded action funnel, structured handoff reports, sentinel-based budget loops, coordinate resize algebra, marker annotation grammar. Adapt host-specific integration: pyautogui/pytesseract/UNO/wmctrl specifics, OSWorld env controllers, sudo password literals ('osworld-public-evaluation'). Omit product behavior: benchmark harness entrypoints, GitHub-release knowledge-base downloads, the s1/s2/s2_5 generations (superseded architecture kept for reproduction).
