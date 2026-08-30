<!-- capsule-v2 -->
# cli-boot-ladder — In what order does main() gate startup, and which gates silently break under `python -O` or a wrong CWD?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** What is the exact boot ladder of the CLI composition root and where are its fragile edges?

## Boot-ladder seam
**Path/Symbol:** `gpt_engineer/applications/cli/main.py:main` (:281-557; body :431-557); helpers `load_env_if_needed` (:71-90), `get_system_info` (:243-251), `get_installed_packages` (:254-264), `format_installed_packages` (:267-268).
**Signature:** `main(project_path=".", model=os.environ.get("MODEL_NAME","gpt-4o"), temperature=0.1, improve_mode=False, lite_mode=False, clarify_mode=False, self_heal_mode=False, azure_endpoint="", use_custom_preprompts=False, llm_via_clipboard=False, verbose=False, debug=False, prompt_file="prompt", entrypoint_prompt_file="", image_directory="", use_cache=False, skip_file_selection=False, no_execution=False, sysinfo=False, diff_timeout=3)`.
**Data Shape:** typer command; 20 options; produces in-memory `AI`, `Prompt`, `DiskMemory`, `DiskExecutionEnv`, `CliAgent`, `FileStore` before any side effect.

### Decisive source
```python
# :443-454 validation exists TWICE — once loud, once assert (stripped under -O)
if improve_mode and (clarify_mode or lite_mode):
    typer.echo("Error: Clarify and lite mode are not compatible with improve mode.")
    raise typer.Exit(code=1)
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
if use_cache:
    set_llm_cache(SQLiteCache(database_path=".langchain.db"))   # CWD-relative!
if improve_mode:
    assert not (clarify_mode or lite_mode), "Clarify and lite mode are not active for improve mode"
load_env_if_needed()
# :500-501 per-run log rotation into <project>/.gpteng/memory
memory = DiskMemory(memory_path(project_path))
memory.archive_logs()
```

**Flow:** debug?→`sys.excepthook = lambda *_: pdb.pm()` (:431-434) → sysinfo?→print+Exit (:436-440) → loud mode validation → logging level → optional SQLiteCache → redundant assert → env load (`load_dotenv()` twice + cwd `.env`, sets `openai.api_key` globally) → `ClipboardAI | AI(model, temperature, azure_endpoint)` → `load_prompt` → vision gate nulls `prompt.image_urls` if `not ai.vision` (:479-480) → pick `code_gen_fn ∈ {clarified_gen, lite_gen, gen_code}` and `execution_fn ∈ {self_heal, execute_entrypoint}` → PrepromptsHolder → memory+archive_logs → DiskExecutionEnv → `CliAgent.with_default_config(...)` → FileStore → `if not no_execution:` improve|generate tails + stage + push → cost tail ALWAYS runs (:552-557).
**Invariant:** (1) The improve-incompatibility check is enforced loudly AND as an assert — porting only the assert loses the guard entirely under `python -O`. (2) `.langchain.db` cache lands in the PROCESS CWD, not the project path — same prompt from another directory misses the cache. (3) `no_execution=True` skips agent execution, staging, AND push (pure dry-run), but token/cost reporting still executes after it. (4) `MODEL_NAME` env default is captured when the module is IMPORTED (typer Option default), not at invocation. (5) TRAP: `get_installed_packages` returns `str(e)` on failure, but `format_installed_packages` calls `.items()` on it — a failing `pip list --format=json` turns `--sysinfo` into AttributeError; keep the happy-path assumption explicit when porting. (6) `archive_logs()` rotates prior logs every single run — memory dir is per-run-reset for logs but persistent for history.
**Probe:** `tests/applications/cli/test_main.py:179-191` (`test_clarify_lite_improve_mode_generate_project` builds improve+lite+clarify args via the DefaultArgumentsMain dataclass harness :60-64 and asserts `pytest.raises(typer.Exit)` — pins the loud validation branch).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "main improve_mode clarify lite validation set_llm_cache archive_logs", limit: 10 });
```

## Verdict
Adopt the ordered gate ladder with the loud-validation-before-assert duplication and the always-runs accounting tail; adapt option names/logging framework to host CLI; omit ClipboardAI transport and pdb excepthook unless porting interactive debugging too. Caveats: no direct test pins the assert twin or the sysinfo error-shape trap (evidence is source-read only); pytest runner blocked in lane (missing deps), so probe evidence is the test's source text.
