<!-- capsule-v2 -->
# self-heal-exec-loop — How does the agent close the loop from runtime failure back to a code fix?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the execute→diagnose→repair cycle's trigger condition, attempt budget, and message shape?

## Self-heal loop seam
**Path/Symbol:** `gpt_engineer/tools/custom_steps.py:self_heal` (:40-119); budget `MAX_SELF_HEAL_ATTEMPTS = 10` (:19).
**Signature:** `self_heal(ai, execution_env, files_dict, prompt=None, preprompts_holder=None, memory=None, diff_timeout=3) -> FilesDict`.
**Data Shape:** Runs `files_dict["run.sh"]` via `popen` + `communicate()`; repairs routed through improve_fn (unified-diff plane).

### Decisive source
```python
while attempts < MAX_SELF_HEAL_ATTEMPTS:
    attempts += 1
    timed_out = False
    execution_env.upload(files_dict)
    p = execution_env.popen(files_dict[ENTRYPOINT_FILE])
    stdout_full, stderr_full = p.communicate()
    if (p.returncode != 0 and p.returncode != 2) and not timed_out:
        print("run.sh failed.  The log is:")
        ...
        new_prompt = Prompt(
            f"A program with this specification was requested:\n{prompt}\n, but running it produced the following output:\n{stdout_full}\n and the following errors:\n{stderr_full}. Please change it so that it fulfills the requirements.")
        files_dict = improve_fn(ai, new_prompt, files_dict, memory, preprompts_holder, diff_timeout)
    else:
        break
return files_dict
```

**Flow:** require run.sh → up to 10 cycles: upload → popen (shell=True) → communicate → if exit ∉ {0,2}: feed spec+stdout+stderr as improvement prompt → improve_fn patches via diff plane → loop re-executes PATCHED files; else break.
**Invariant:** (1) Exit code 2 is treated as SUCCESS — deliberate carve-out (common for pytest "tests collected and failed"-style flows and tool conventions); porters routinely miss this and heal-loop forever. (2) `timed_out` is initialized False and NEVER set anywhere — dead flag; timeout handling actually lives in DiskExecutionEnv.run (KeyboardInterrupt/TimeoutError arms) which self_heal BYPASSES by using popen directly. (3) The repair prompt interpolates RAW bytes-decoded output (stdout_full is bytes; f-string renders b'...' repr if bytes not decoded — cosmetic wart, works because model tolerates it). (4) Repairs go through improve_fn ⇒ the ENTIRE salvage/refinement machinery applies; healing budget (10) is independent of edit-refinement budget (2) — worst case 30 LLM calls per heal session. (5) Missing preprompts_holder raises AssertionError BEFORE looping (fail-fast precondition).
**Probe:** `grep -c 'MAX_SELF_HEAL_ATTEMPTS' gpt_engineer/tools/custom_steps.py` → 3 (:19 def, :95 loop, docstring mention :77).
**Probe:** `grep -n 'returncode != 0 and p.returncode != 2' gpt_engineer/tools/custom_steps.py` → the carve-out line.
**Probe:** `grep -n 'popen' gpt_engineer/tools/custom_steps.py` → self_heal uses popen+communicate, NOT .run().

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "self_heal MAX_SELF_HEAL_ATTEMPTS returncode improve_fn", limit: 10 });
```

## Verdict
Adopt the exec-diagnose-repair loop skeleton incl. the exit-code allowlist idea; adapt the allowlist codes and budget to your runner; fix (don't copy) the dead timeout flag and undecoded-bytes interpolation. Selected via CLI `--self-heal` replacing execute_entrypoint as process_code_fn (main.py:491-494).
