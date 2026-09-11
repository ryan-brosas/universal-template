<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# gpt-engineer: Minimal codegen-agent foundations

## Use this for
Use when porting prompt→code→execute→repair agent loops, LLM unified-diff application with self-correction, or minimal injectable-step agent skeletons. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./gen-code-parse-contract.md` — one-shot answer → FilesDict parse contract.
- `./sys-prompt-sandwich.md` — four-file system-prompt composition with FILE_FORMAT substitution.
- `./entrypoint-fence-regex.md` — extracting run.sh from chatty model output.
- `./execute-entrypoint-consent-gate.md` — human consent before executing generated shell code.
- `./improve-loop-refinement-cap.md` — bounded diff-repair retry loop and feedback contract.
- `./salvage-hunks-pipeline.md` — validate-mutate-then-apply ordering; new-file exemption.
- `./hunk-repair-ladder.md` — anchor-finding, comment-relabeling, three-way forward-block repair.
- `./diff-apply-remove-flag.md` — mark-then-sweep positional line editing without index corruption.
- `./diff-parse-timeout-first-wins.md` — ReDoS-safe third-party regex parsing; duplicate-diff dedupe.
- `./similarity-count-ratio.md` — the order-insensitive line-similarity metric behind validation.
- `./self-heal-exec-loop.md` — execute→diagnose→repair loop with exit-code allowlist.
- `./clarified-gen-swap.md` — clarify Q&A transcript reused for generation via persona swap.
- `./agent-abc-injectable-steps.md` — two-method agent ABC; modes as injected functions.
- `./ai-collapse-vision-ladder.md` — message collapsing, vision sniffing, provider branches, backoff.
- `./disk-memory-pathlist-contract.md` — file-KV memory: sorted iteration, image data-URLs, log rotation.
- `./file-selector-toml-context.md` — editor-in-the-loop default-deny context selection.
- `./git-stage-uncommitted-guard.md` — intersect-then-stage undoability before overwriting files.
- `./improve-console-capture.md` — tee-and-swallow crash capture into a sectioned debug log.
- `./preprompts-holder-copy-custom.md` — copy-if-absent prompt-pack provisioning.
- `./token-usage-cost-gate.md` — name-gated cost reporting with local-model fallback.
- `./project-config-toml-roundtrip.md` — comment-preserving config roundtrip, non-default write-back.
- `./workspace-push-compare-flow.md` — diff-review-consent-restore tail before disk push.
- `./cli-boot-ladder.md` — main() startup gate order; `-O` assert trap, CWD-relative cache, no_execution semantics.
- `./load-prompt-contract.md` — prompt file / interactive / entrypoint / image-dir assembly into Prompt with fail-loud validation.
- `./consent-file-latch.md` — `.gpte_consent` one-way durable consent latch; declining never persists.
- `./human-review-question-tree.md` — y/n/u terminal review tree → Review with raw-transcript vs typed-null duality.
- `./learning-envelope-session-id.md` — Learning payload wiring incl. whole-memory snapshot and tempdir-persistent session id.
- `./send-learning-truncation-ladder.md` — RuntimeError-only 32KiB tail-truncation retry ladder; fail-open telemetry.

## Capsule map
- **Codegen plane** — `gen-code-parse-contract`, `sys-prompt-sandwich`, `entrypoint-fence-regex`: one-shot generation from a composed system prompt into a parsed FilesDict plus an extracted `run.sh`.
- **Diff plane** — `improve-loop-refinement-cap`, `salvage-hunks-pipeline`, `hunk-repair-ladder`, `diff-apply-remove-flag`, `diff-parse-timeout-first-wins`, `similarity-count-ratio`: safe parsing, validation, correction, and application of LLM unified diffs against drifted sources.
- **Repair loops** — `self-heal-exec-loop`, `clarified-gen-swap`, `improve-console-capture`: runtime-error-driven healing, clarify-then-build reuse, and post-mortem capture.
- **Agent core** — `agent-abc-injectable-steps`, `ai-collapse-vision-ladder`, `execute-entrypoint-consent-gate`: the two-method agent interface with function-injected modes and the provider/capability-aware LLM seam.
- **Workspace & safety** — `disk-memory-pathlist-contract`, `file-selector-toml-context`, `git-stage-uncommitted-guard`, `workspace-push-compare-flow`: deterministic memory, default-deny context selection, pre-overwrite staging, consented writes.
- **Config & accounting** — `preprompts-holder-copy-custom`, `project-config-toml-roundtrip`, `token-usage-cost-gate`: prompt packs, user-editable TOML config, spend reporting.
- **CLI composition & telemetry** — `cli-boot-ladder`, `load-prompt-contract`, `consent-file-latch`, `human-review-question-tree`, `learning-envelope-session-id`, `send-learning-truncation-ladder`: the main() boot ladder, Prompt assembly contract, and the consent/review/session telemetry kernel that ships learnings fail-open under size limits.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
gpt-engineer (MIT), `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory project `gpt-engineer` (1,143 nodes / 4,292 edges, FULL mode, head == base at the 2026-08-26 first-run re-index of this checkout; parse_partial ×1 = tox.ini only, none cited). The 2026-08-26 deepening pass added the six CLI/telemetry capsules and repaired every citation from the retired graph name `ext-gpt-engineer` (same commit; edge delta = indexer drift) to the live project.

## Full view (memory graph)
Revalidate `gpt-engineer` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: diff parse/validate/apply pipeline, similarity metric, refinement caps, agent ABC + injected steps, consent gates. Adapt host-specific integrations: LangChain/OpenAI/Azure/Anthropic plumbing, editor UX, black linting, tiktoken pricing, RudderStack telemetry. Omit product behavior: benchmark harness (`benchmark/`), gptengineer.app cloud integration, legacy `projects/example*` scripts, clipboard-human-in-the-loop transport.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-abc-injectable-steps.md`](./agent-abc-injectable-steps.md)
- [`ai-collapse-vision-ladder.md`](./ai-collapse-vision-ladder.md)
- [`clarified-gen-swap.md`](./clarified-gen-swap.md)
- [`cli-boot-ladder.md`](./cli-boot-ladder.md)
- [`consent-file-latch.md`](./consent-file-latch.md)
- [`diff-apply-remove-flag.md`](./diff-apply-remove-flag.md)
- [`diff-parse-timeout-first-wins.md`](./diff-parse-timeout-first-wins.md)
- [`disk-memory-pathlist-contract.md`](./disk-memory-pathlist-contract.md)
- [`entrypoint-fence-regex.md`](./entrypoint-fence-regex.md)
- [`execute-entrypoint-consent-gate.md`](./execute-entrypoint-consent-gate.md)
- [`file-selector-toml-context.md`](./file-selector-toml-context.md)
- [`gen-code-parse-contract.md`](./gen-code-parse-contract.md)
- [`git-stage-uncommitted-guard.md`](./git-stage-uncommitted-guard.md)
- [`human-review-question-tree.md`](./human-review-question-tree.md)
- [`hunk-repair-ladder.md`](./hunk-repair-ladder.md)
- [`improve-console-capture.md`](./improve-console-capture.md)
- [`improve-loop-refinement-cap.md`](./improve-loop-refinement-cap.md)
- [`learning-envelope-session-id.md`](./learning-envelope-session-id.md)
- [`load-prompt-contract.md`](./load-prompt-contract.md)
- [`preprompts-holder-copy-custom.md`](./preprompts-holder-copy-custom.md)
- [`project-config-toml-roundtrip.md`](./project-config-toml-roundtrip.md)
- [`salvage-hunks-pipeline.md`](./salvage-hunks-pipeline.md)
- [`self-heal-exec-loop.md`](./self-heal-exec-loop.md)
- [`send-learning-truncation-ladder.md`](./send-learning-truncation-ladder.md)
- [`similarity-count-ratio.md`](./similarity-count-ratio.md)
- [`sys-prompt-sandwich.md`](./sys-prompt-sandwich.md)
- [`token-usage-cost-gate.md`](./token-usage-cost-gate.md)
- [`workspace-push-compare-flow.md`](./workspace-push-compare-flow.md)
