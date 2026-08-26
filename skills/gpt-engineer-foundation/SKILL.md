---
name: gpt-engineer-foundation
description: "Minimal codegen-agent foundation"
---
# gpt-engineer: Minimal codegen-agent foundations

## Use this for
Use when porting prompt→code→execute→repair agent loops, LLM unified-diff application with self-correction, or minimal injectable-step agent skeletons. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/gen-code-parse-contract.md` — one-shot answer → FilesDict parse contract.
- `references/sys-prompt-sandwich.md` — four-file system-prompt composition with FILE_FORMAT substitution.
- `references/entrypoint-fence-regex.md` — extracting run.sh from chatty model output.
- `references/execute-entrypoint-consent-gate.md` — human consent before executing generated shell code.
- `references/improve-loop-refinement-cap.md` — bounded diff-repair retry loop and feedback contract.
- `references/salvage-hunks-pipeline.md` — validate-mutate-then-apply ordering; new-file exemption.
- `references/hunk-repair-ladder.md` — anchor-finding, comment-relabeling, three-way forward-block repair.
- `references/diff-apply-remove-flag.md` — mark-then-sweep positional line editing without index corruption.
- `references/diff-parse-timeout-first-wins.md` — ReDoS-safe third-party regex parsing; duplicate-diff dedupe.
- `references/similarity-count-ratio.md` — the order-insensitive line-similarity metric behind validation.
- `references/self-heal-exec-loop.md` — execute→diagnose→repair loop with exit-code allowlist.
- `references/clarified-gen-swap.md` — clarify Q&A transcript reused for generation via persona swap.
- `references/agent-abc-injectable-steps.md` — two-method agent ABC; modes as injected functions.
- `references/ai-collapse-vision-ladder.md` — message collapsing, vision sniffing, provider branches, backoff.
- `references/disk-memory-pathlist-contract.md` — file-KV memory: sorted iteration, image data-URLs, log rotation.
- `references/file-selector-toml-context.md` — editor-in-the-loop default-deny context selection.
- `references/git-stage-uncommitted-guard.md` — intersect-then-stage undoability before overwriting files.
- `references/improve-console-capture.md` — tee-and-swallow crash capture into a sectioned debug log.
- `references/preprompts-holder-copy-custom.md` — copy-if-absent prompt-pack provisioning.
- `references/token-usage-cost-gate.md` — name-gated cost reporting with local-model fallback.
- `references/project-config-toml-roundtrip.md` — comment-preserving config roundtrip, non-default write-back.
- `references/workspace-push-compare-flow.md` — diff-review-consent-restore tail before disk push.
- `references/cli-boot-ladder.md` — main() startup gate order; `-O` assert trap, CWD-relative cache, no_execution semantics.
- `references/load-prompt-contract.md` — prompt file / interactive / entrypoint / image-dir assembly into Prompt with fail-loud validation.
- `references/consent-file-latch.md` — `.gpte_consent` one-way durable consent latch; declining never persists.
- `references/human-review-question-tree.md` — y/n/u terminal review tree → Review with raw-transcript vs typed-null duality.
- `references/learning-envelope-session-id.md` — Learning payload wiring incl. whole-memory snapshot and tempdir-persistent session id.
- `references/send-learning-truncation-ladder.md` — RuntimeError-only 32KiB tail-truncation retry ladder; fail-open telemetry.

## Capsule map
- **Codegen plane** — `gen-code-parse-contract`, `sys-prompt-sandwich`, `entrypoint-fence-regex`: one-shot generation from a composed system prompt into a parsed FilesDict plus an extracted `run.sh`.
- **Diff plane** — `improve-loop-refinement-cap`, `salvage-hunks-pipeline`, `hunk-repair-ladder`, `diff-apply-remove-flag`, `diff-parse-timeout-first-wins`, `similarity-count-ratio`: safe parsing, validation, correction, and application of LLM unified diffs against drifted sources.
- **Repair loops** — `self-heal-exec-loop`, `clarified-gen-swap`, `improve-console-capture`: runtime-error-driven healing, clarify-then-build reuse, and post-mortem capture.
- **Agent core** — `agent-abc-injectable-steps`, `ai-collapse-vision-ladder`, `execute-entrypoint-consent-gate`: the two-method agent interface with function-injected modes and the provider/capability-aware LLM seam.
- **Workspace & safety** — `disk-memory-pathlist-contract`, `file-selector-toml-context`, `git-stage-uncommitted-guard`, `workspace-push-compare-flow`: deterministic memory, default-deny context selection, pre-overwrite staging, consented writes.
- **Config & accounting** — `preprompts-holder-copy-custom`, `project-config-toml-roundtrip`, `token-usage-cost-gate`: prompt packs, user-editable TOML config, spend reporting.
- **CLI composition & telemetry** — `cli-boot-ladder`, `load-prompt-contract`, `consent-file-latch`, `human-review-question-tree`, `learning-envelope-session-id`, `send-learning-truncation-ladder`: the main() boot ladder, Prompt assembly contract, and the consent/review/session telemetry kernel that ships learnings fail-open under size limits.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
gpt-engineer (MIT), `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory project `gpt-engineer` (1,143 nodes / 4,292 edges, FULL mode, head == base at the 2026-08-26 first-run re-index of this checkout; parse_partial ×1 = tox.ini only, none cited). The 2026-08-26 deepening pass added the six CLI/telemetry capsules and repaired every citation from the retired graph name `ext-gpt-engineer` (same commit; edge delta = indexer drift) to the live project.

## Full view (memory graph)
Revalidate `gpt-engineer` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: diff parse/validate/apply pipeline, similarity metric, refinement caps, agent ABC + injected steps, consent gates. Adapt host-specific integrations: LangChain/OpenAI/Azure/Anthropic plumbing, editor UX, black linting, tiktoken pricing, RudderStack telemetry. Omit product behavior: benchmark harness (`benchmark/`), gptengineer.app cloud integration, legacy `projects/example*` scripts, clipboard-human-in-the-loop transport.
