<!-- capsule-v2 -->
# Docker backend tar choreography — how do files move in/out of ephemeral containers with NO host mounts?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How does a stateless-container code sandbox persist working-dir files across calls and report artifacts without ever binding a host path into a container?

## Archive-only I/O over a host-persistent working dir
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/docker.py:DockerCodingSandbox._run_container_sync` (L476–616); `_collect_working_dir_inputs` (L751–770); `_tar_files` (L773–786); `_extract_container_dir` (L801–837); `_RESERVED_WORKING_DIR_SUBDIRS` (L99).
**Signature:** `_run_container_sync(command, src_dir, timeout, network_enabled, staged_inputs) -> (exit_code, stdout, stderr)`; `_collect_working_dir_inputs(working_dir) -> dict[rel_path, bytes]`; `_extract_container_dir(container, container_path, local_dir) -> None`.
**Data Shape:** One instance = ONE host working dir (`alcs-docker-<10hex>` under realpath'd tempdir) holding reserved subtrees `_src/`, `output/`, `deps_python/`, `node_modules/`. Every call builds a FRESH container; persistence lives entirely on the host and is re-archived in each time.

### Decisive source
```python
# put_archive sequence per run (order matters):
container.put_archive("/", _tar_empty_dir("src", mode=0o777))   # mkdir first
if staged_inputs:                       # upload_file()'s lifetime staging
    container.put_archive("/src", _tar_files(staged_inputs))
container.put_archive("/src", _tar_directory(src_dir))  # entry file LAST
...
os.makedirs(self._output_dir, exist_ok=True)
_extract_container_dir(container, "/output", self._output_dir)
_extract_container_dir(container, "/src", src_dir)   # cwd-written files mirrored back

# traversal guard inside _extract_container_dir:
target = os.path.realpath(os.path.join(local_dir, member.name))
if not target.startswith(resolved_root + os.sep) and target != resolved_root:
    logger.warning("Skipping tar member with path traversal: %s -> %s", ...)
    continue
```

**Flow:** write entry into fresh `_src/` → read ALL lifetime-staged inputs once (`staged_inputs`, also the promotion baseline) → snapshot `output/` mtimes BEFORE the run → create container (mem/nano_cpus/tmpfs caps, `network_mode="none"`+`network_disabled=True` unless BOTH flags allow egress via the dedicated bridge) → mkdir `/src`,`/output`,`/deps`,`/node_modules` → archive staged inputs then entry dir → start, `wait(timeout)` w/ kill-on-timeout → extract `/output` AND `/src` back (merge, never clear) → `finally`: `container.remove(force=True)` + `client.close()`.
**Invariant:** (1) NO host-path volume mount anywhere — everything crosses via `put_archive`/`get_archive`, so this works under DinD where host paths don't exist on the daemon FS. (2) Reserved subdirs are archived through their OWN dedicated calls and excluded from the generic sweep — re-including double-archives or lands files at wrong container paths. (3) `output/` merges across calls (never cleared), so artifact listing MUST diff against a pre-run mtime snapshot or call 2 re-reports call 1's outputs. (4) Tar extraction skips any member resolving outside the target root.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_docker_coding_sandbox.py::test_second_call_does_not_re_report_first_calls_output` (:188), `::test_second_call_reports_only_its_own_new_output_file` (:219), `::test_staged_input_is_archived_into_src_before_run` (:262), `::test_unchanged_staged_input_not_reported_as_artifact` (:281), `::test_modified_staged_input_is_reported_as_artifact` (:302), `::test_extract_container_dir_blocks_path_traversal` (:551).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "DockerCodingSandbox _run_container_sync put_archive _collect_working_dir_inputs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the archive-only transfer model + reserved-subdir partitioning + pre-run mtime baselines for any ephemeral-container executor; adapt image/network/env names (all constructor args by design — no PipesHub literals in-module) and spool threshold (16MiB). Omit PipesHub's adapter layer wiring. Direct tests read at HEAD (~35 cases incl. fake-container harness). Test paths are outside the graph index at this pin (freshness: missing) — probes pinned from on-disk reads.
