<!-- capsule-v2 -->
# Cwd-artifact promotion — how do files the program wrote to its cwd become artifacts on a backend that only extracts /output?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Models overwhelmingly write outputs to their cwd, not `$OUTPUT_DIR` — how does the Docker backend capture cwd-written files without re-reporting staged inputs as fresh artifacts?

## Baseline-diffed /src mirror-back promotion
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/docker.py:DockerCodingSandbox._promote_src_artifacts` (L393–440); `_snapshot_mtimes` (L102–120); `_list_output_artifacts` (L442–472).
**Signature:** `_promote_src_artifacts(src_dir, entry, staged_inputs) -> list[str]`; `_list_output_artifacts(before: dict[str, float] | None) -> list[str]`.
**Data Shape:** `staged_inputs` is the SAME `{relative_path: bytes}` map archived into `/src` pre-run — it doubles as the "unchanged" baseline. Promotion moves (not copies) `/src`-mirrored files up into the working dir and reports them as artifacts.

### Decisive source
```python
for dirpath, _dirnames, filenames in os.walk(src_dir):
    for fname in filenames:
        rel = os.path.relpath(full, src_dir)
        if rel == entry:
            continue                                  # entry never an artifact
        baseline = staged_inputs.get(rel)
        if baseline is not None:
            current = open(full, "rb").read()
            if current == baseline:
                skipped_unchanged.append(rel)         # staged input, unmodified
                continue                              # → NOT reported as produced
        dest = os.path.join(self._working_dir, rel)
        shutil.move(full, dest)                       # promote out of _src
        promoted.append(rel)

# execute() combines BOTH artifact sources, sorted for determinism:
artifacts  = self._list_output_artifacts(output_before)   # mtime-diffed /output
artifacts.extend(self._promote_src_artifacts(src_dir, entry, staged_inputs))
```

**Flow:** run finishes → extract `/src` over host `src_dir` (merge) → walk it: skip entry file; skip any file byte-identical to its staged baseline; move everything else into the working dir and report → merge with mtime-diffed `/output` listing → sort.
**Invariant:** (1) The local backend catches cwd writes via its whole-dir mtime diff; Docker's extraction boundary is `/output` ONLY — without explicit `/src` promotion every cwd-written file dies with the container (this capsule restores backend parity). (2) A staged input must be reported as an artifact ONLY if the program actually rewrote it (same path, different bytes); content equality, not mtime, decides. (3) Read staged inputs ONCE per call — the exact same bytes are both what gets archived in and what promotion diffs against (no second, racy disk read).
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_docker_coding_sandbox.py::test_file_written_to_container_cwd_is_reported_as_artifact` (:152), `::test_cwd_and_output_dir_artifacts_are_combined` (:173), `::test_unchanged_staged_input_not_reported_as_artifact` (:281), `::test_modified_staged_input_is_reported_as_artifact` (:302).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_promote_src_artifacts _list_output_artifacts staged_inputs artifacts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-source artifact collection (`$OUTPUT_DIR` diff + cwd promotion with staged-byte baselines) for ANY sandbox whose output extraction boundary is narrower than the program's cwd; adapt the reserved-dir names and log verbosity. Coverage caveat: E2B backend uses whole-listing set difference (`after - before - {entry}`) instead of mtimes — equivalent intent, weaker under same-mtime races; don't mix the two mechanisms in one backend. Test paths outside graph index at this pin — probes from on-disk reads.
