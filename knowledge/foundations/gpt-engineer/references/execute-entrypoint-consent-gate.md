<!-- capsule-v2 -->
# execute-entrypoint-consent-gate — Where is the human-in-the-loop before generated code executes?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What gates execution of AI-written shell code, and what is the exact consent protocol?

## Execution consent seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:execute_entrypoint` (:205-268).
**Signature:** `execute_entrypoint(ai, execution_env: BaseExecutionEnv, files_dict, prompt=None, preprompts_holder=None, memory=None) -> FilesDict`.
**Data Shape:** Reads `files_dict["run.sh"]`; returns the SAME FilesDict unchanged regardless of consent (execution result is not folded back into files).

### Decisive source
```python
if ENTRYPOINT_FILE not in files_dict:
    raise FileNotFoundError("The required entrypoint " + ENTRYPOINT_FILE + " does not exist in the code.")
command = files_dict[ENTRYPOINT_FILE]
print(colored("Do you want to execute this code? (Y/n)", "red"))
print(command)
if input("").lower() not in ["", "y", "yes"]:
    print("Ok, not executing the code.")
    return files_dict
...
execution_env.upload(files_dict).run(f"bash {ENTRYPOINT_FILE}")
```

**Flow:** missing-run.sh guard → display full script → blocking `input("")` → empty/y/yes proceeds → upload FilesDict into env → run `bash run.sh` in env's cwd.
**Invariant:** (1) Consent default is YES (empty string passes) — the gate informs rather than blocks; flip this deliberately when porting to autonomous agents. (2) The script ALWAYS runs via `bash run.sh` — the uploaded file's shebang is ignored. (3) `upload(files_dict)` returns the env itself (fluent), then `.run(...)`; DiskExecutionEnv.run streams stdout/stderr live, kills on KeyboardInterrupt ("You can press ctrl+c *once*"), and returns `(stdout, stderr, returncode)` which this step DISCARDS. (4) This function is also the DEFAULT `process_code_fn`; self_heal mode replaces it (see self-heal capsule) and skips the consent prompt entirely.
**Probe:** `grep -c '\["", "y", "yes"\]' gpt_engineer/core/default/steps.py` → 1 (consent list exists exactly once).
**Probe:** `grep -n 'bash {ENTRYPOINT_FILE}' gpt_engineer/core/default/steps.py` → the f-string run site.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "execute_entrypoint execution_env upload run consent", limit: 10 });
```

## Verdict
Adopt the show-then-confirm pattern for any code-executing agent; adapt the consent default to your autonomy policy (self-heal mode demonstrates a promptless variant); omit termcolor decoration. Direct test: `tests/core/default/test_disk_execution_env.py::test_missing_entrypoint` pins the FileNotFoundError arm.
