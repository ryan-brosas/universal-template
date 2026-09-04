<!-- capsule-v2 -->
# Sandbox uv command normalization — why must sandbox shells NEVER see bare `pip`, `python -m pip`, or `uv run`, and what exact retry ladder replaces them?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An LLM in a venv-backed sandbox habitually installs with pip and validates imports with `python -m <pkg>` — what prompt-level command contract makes installs/verification/runs succeed without breaking on the sandbox's missing pip CLI and project-sync hazards?

## Prompt-embedded command contract
**Path/Symbol:** `src/cuga/backend/skills/sandbox_uv.py` (`SANDBOX_UV_COMMAND_NORMALIZATION` :72-85 composing :9-70), consumed via `guidance.py` (`LOAD_SKILL_COMMAND_NORMALIZATION` = "Command normalization override..." + the block) into every `SkillRegistry.load_skill` output.
**Signature:** module constants only — no callables. `SANDBOX_UV_PIP_INSTALL = "uv pip install <package>"`; `SANDBOX_RUN_FALLBACK`; `SANDBOX_RUN_COMMAND_RETURN`; `SANDBOX_WRITE_THEN_RUN`; `SANDBOX_WORKSPACE_PATHS`.
**Data Shape:** One composed text blob injected into load_skill output (and available standalone). It is a BEHAVIORAL contract for a code-executing agent, versioned by tests that assert substrings — treat edits as API changes.

### Decisive source
```python
# sandbox_uv.py:15-22 — import verification ladder; sandbox venvs ship NO pip CLI
# and most packages are not runnable modules:
#   (1) python -c "import <pkg>; print('ok')"   — preferred
#   (2) uv pip show <package>
#   (3) uv pip list | grep -i <package>
# NEVER: python -m pip / pip show / pip list / python -m <package>

# :26-34 — run fallback: direct python FIRST (venv already active), then EXACTLY ONE
# retry with the --no-project flag:
"If that fails ... retry once with `uv run --no-project python -c '...'`"
"Do not retry with bare `uv run`, `uv run --active`, `python -m pip`, or `pip`."

# :36-40 — WHY bare uv run is forbidden: it syncs/builds the PARENT Cuga project
SANDBOX_UV_FORBIDDEN = ("Never use bare `uv run` (syncs/builds the parent Cuga project), "
    "`uv run --active`, `pip` / ... or `python -m <package>` to validate imports.")

# :50-61 — return-shape contract: stdout plain string, stderr appended ONLY on
# failure after the literal marker "\n[stderr]\n"; JSON parse recipe:
json.loads(out.split("\n[stderr]\n", 1)[0].strip())
```

**Flow:** skill loaded → normalization block lands in context before STEP 1 → agent installs via `uv pip install` → verifies import via the 3-step ladder → runs scripts written in a PRIOR step (`write_file` first, confirm `File written:` prefix, then run the SAME path) → parses output per the string contract, treating `[stderr]` / `can't open file` / `head: None` / `exited with status` / `[run_command error]` as hard failure signals: print full output, fix, STOP — never regex-parse or infer schema from failed output.
**Invariant:** (1) The marker `\n[stderr]\n` appears ONLY on failure, so its absence IS the success signal — any tooling that appends stderr unconditionally breaks every consumer of this contract. (2) Bare `uv run` is not a style nit: it resolves/syncs the parent project inside the sandbox (slow, mutating, can fail the whole turn). (3) Node/npm are explicitly out of uv's jurisdiction: plain `node ...` / `npm install ...`, never `uv npm` or `uv run node`. (4) Workspace paths are workspace-relative everywhere (`./uploads/foo.json` works in tools AND `open()`); absolute `/workspace/...` is auto-rewritten to `./` in shell.
**Probe:** `tests/unit/test_sandbox_uv_guidance.py::test_sandbox_uv_guidance_forbids_bare_uv_run` (:6 asserts every key phrase incl. `"split('\\n[stderr]\\n', 1)"` and `"only on failure"`), `::test_load_skill_includes_sandbox_uv_guidance` (:21 SANDBOX_UV_COMMAND_NORMALIZATION rides every load_skill output); `tests/unit/test_skill_loader.py::test_skill_registry_load_skill_includes_install_normalization_guidance` (:97 asserts install-normalization phrases present).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "SANDBOX_UV_COMMAND_NORMALIZATION LOAD_SKILL_GUIDANCE run_command uv pip install", limit: 10 });
```

## Verdict
Adopt the whole constant block verbatim if your host also uses uv-venv sandboxes with stdout-capture execution; otherwise keep the SHAPE — install-tool pinning, one bounded retry with an explicit flag, failure-marker string contract, write-then-run-same-path discipline — adapted to your package manager. Omit nothing from the forbidden list when porting to uv sandboxes: each entry corresponds to a real failure mode (missing pip CLI, project sync, wrong interpreter).
