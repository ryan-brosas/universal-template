<!-- capsule-v2 -->
# Eval Review Viewer — how does a zero-dependency harness turn a workspace of eval runs into a reviewable, feedback-collecting page?

**Source:** anthropics/skills (skill-creator/eval-viewer) Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** What are the discovery, embedding, and feedback contracts that make eval results comparable and iterable across skill-improvement iterations?

## Run discovery + data-URI embedding + regenerate-on-refresh server
**Path/Symbol:** `skills/skill-creator/eval-viewer/generate_review.py` (`find_runs` :60–82 recursive discovery stopping at any dir containing `outputs/`, skip-list node_modules/.git/__pycache__/skill/inputs; `build_run` :85–146 prompt ladder eval_metadata.json → transcript.md `## Eval Prompt` section → "(No prompt found)", grading.json from run or parent; `embed_file` :149–210 five-way extension split; `generate_html` :250–281 template marker replace; `do_GET`/`do_POST` :332–380; `_kill_port` :288–306).
**Signature:** `python generate_review.py <workspace> [--port 3117] [--skill-name N] [--previous-workspace P] [--benchmark B] [--static OUT]`.
**Data Shape:** run = directory with `outputs/`; embedded payload = `{skill_name, runs[], previous_feedback{run_id→text}, previous_outputs}` injected by replacing the literal `/*__EMBEDDED_DATA__*/` marker in viewer.html. Embedding classes: TEXT_EXTENSIONS → inline text; IMAGE/PDF → base64 data URI; .xlsx → raw b64 (viewer renders via SheetJS); else binary download link. Feedback = `{reviews:[{run_id, feedback}]}` auto-saved to workspace feedback.json.

### Decisive source
```python
outputs_dir = current / "outputs"
if outputs_dir.is_dir():
    run = build_run(root, current)
    ...
    return                      # do NOT descend into a run
```
```python
return template.replace("/*__EMBEDDED_DATA__*/", f"const EMBEDDED_DATA = {data_json};")
```

**Flow:** discover runs (first `outputs/` wins, no recursion past it) → embed every output file so ONE self-contained HTML carries everything (no asset server needed; --static mode ships it as a file) → serve on 127.0.0.1:3117 after killing stale listeners (lsof→SIGTERM, fallback ephemeral port) → REGENERATE HTML per GET so a browser refresh picks up new outputs without server restart → reviewer feedback POSTs whole JSON object, validated for `reviews` key, written with indent=2 → next iteration passes `--previous-workspace` so old outputs+feedback render inline as context.
**Invariant:** Metadata files (transcript.md/user_notes.md/metrics.json) are excluded from output listings but ARE read as grading inputs — separation of evidence-for-human vs evidence-for-grader. Run identity is path-derived (`run_dir.relative_to(root)` slash→dash), which is what makes feedback survive regeneration. Everything is stdlib-only by design.
**Probe:** No unit tests upstream. Deterministic probes (anchors re-derived & executed byte-exact 2026-08-24 from repo root): `grep -c '__EMBEDDED_DATA__' skills/skill-creator/eval-viewer/generate_review.py` = 1 and same for `viewer.html` = 1 (template marker present both sides); skip-list + stop-at-outputs pinned by `find_runs` source :60–82 (`node_modules/.git/__pycache__/` skip-list line verified); discovery/500-behavior remain fixture-level observations — recorded honestly, not re-executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "find_runs build_run EMBEDDED_DATA", limit: 10 });
```

## Verdict
Adopt the discovery/embedding/regenerate-on-refresh contracts for any human-in-the-loop eval harness. Adapt the xlsx/SVG MIME overrides and port choice. Omit the viewer.html internals (template-owned). Caveat: script-only pinning; pairs with eval-harness.md (execution side) — this capsule is the review side.
