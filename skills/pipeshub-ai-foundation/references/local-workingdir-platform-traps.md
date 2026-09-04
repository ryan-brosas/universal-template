<!-- capsule-v2 -->
# Short-tmpdir + realpath working dir — why does the sandbox directory name length and symlink resolution matter?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What two platform landmines (macOS /private/var symlink, sockaddr_un 104-byte limit) must a local sandbox dodge when choosing its on-disk directory?

## realpath for Seatbelt, 10-hex suffix for Unix sockets
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/local.py:LocalCodingSandbox.__init__` (L47–90); `provision` (L100–113); `_resolve_path` (L201–209).
**Signature:** `working_dir = os.path.realpath(tempfile.gettempdir()/f"alcs-{sandbox_id.replace('-','')[:10]}")` — full UUID kept ONLY as external `sandbox_id`.
**Data Shape:** `output/` pre-created in provision BEFORE any mtime snapshot (`_snapshot_mtimes` records files not dirs — an absent output dir would make first-run outputs look right by accident); listing ignores `node_modules/.venv/__pycache__/.git`.

### Decisive source
```python
# realpath matters: on macOS tempfile.gettempdir() returns a path under the
# /var -> /private/var symlink, and Seatbelt's `subpath` matching operates on
# the RESOLVED path — an unresolved working_dir would cause every confined
# write inside it to be denied with a spurious EPERM.
#
# The directory name is deliberately SHORT (not the full UUID) — HOME/TMPDIR
# are pointed at this directory (see sanitized_subprocess_env), and tools like
# tsx create Unix domain sockets under TMPDIR for internal IPC; sockaddr_un
# has a ~104-byte path limit, and a long tempdir-plus-UUID path combined with
# the tool's own subdirectory can exceed it, causing a confusing EINVAL from
# listen() that looks unrelated to path length.
```

**Flow:** init (realpath + short name) → provision creates dir + `output/` + registers with exit-cleanup → execute logs existing files, installs packages via EnvironmentManager if requested, delegates to CodeExecutor → reflection composes ErrorAnalysis on failure → destroy rmtree + unregister.
**Invariant:** (1) The path handed to confinement profiles MUST be the resolved one or macOS denies writes inside your own sandbox. (2) Any directory that will hold AF_UNIX sockets must keep its whole path chain short — TMPDIR redirection makes the sandbox dir the socket root. (3) External identity (`sandbox_id`, full uuid4) is decoupled from on-disk naming. (4) Same traversal guard as every backend: resolved join + prefix check, escapes raise ValueError.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_local_coding_sandbox.py::test_provision_creates_the_output_directory` (:29), `::test_provision_is_idempotent` (:36), `::test_escaping_paths_are_rejected` (:74), `::test_output_dir_alias_reads_the_real_file` (:79).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "LocalCodingSandbox working_dir realpath short_suffix provision", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt realpath-before-confinement + short-dir-name discipline verbatim (both are platform facts, not style); adapt the name prefix. Omit PipesHub's compose wiring. Direct tests cover provision/traversal; the two platform rationales are documented-in-code with no dedicated test — carry them as comments in any port.
