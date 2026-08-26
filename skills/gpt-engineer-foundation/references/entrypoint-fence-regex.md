<!-- capsule-v2 -->
# entrypoint-fence-regex — How is a runnable install-and-run script extracted from a chatty LLM answer?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** How does gen_entrypoint pull shell commands out of prose and why are ALL fenced blocks joined?

## Entrypoint extraction seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:gen_entrypoint` (:153-202); constant `gpt_engineer/core/default/paths.py:ENTRYPOINT_FILE = "run.sh"` (:49 AND duplicated :51).
**Signature:** `gen_entrypoint(ai, prompt, files_dict, memory, preprompts_holder) -> FilesDict`.
**Data Shape:** Output is a single-key FilesDict `{run.sh: "<all commands>"}`; input chat may contain explanations around the fences.

### Decisive source
```python
user_prompt = prompt.entrypoint_prompt
if not user_prompt:
    user_prompt = """
    Make a unix script that
    a) installs dependencies
    b) runs all necessary parts of the codebase (in parallel if necessary)
    """
...
chat = messages[-1].content.strip()
regex = r"```\S*\n(.+?)```"
matches = re.finditer(regex, chat, re.DOTALL)
entrypoint_code = FilesDict({ENTRYPOINT_FILE: "\n".join(match.group(1) for match in matches)})
```

**Flow:** default or user entrypoint prompt + full codebase rendered via `files_dict.to_chat()` → entrypoint preprompt ("Do not install globally. Do not use sudo.") → model answer → collect EVERY fenced block body → join with newlines → store as run.sh.
**Invariant:** (1) ALL fences are concatenated into ONE file, ordered by appearance — a model that explains setup in two fenced blocks still yields a working script; prose between blocks is silently dropped. (2) The regex requires a language tag (`\S*` after backticks may be empty but the newline structure ` ```\n ` is mandatory). (3) `execute_entrypoint` later REQUIRES the key `run.sh` to exist or raises FileNotFoundError — the two functions share the filename constant. (4) paths.py declares ENTRYPOINT_FILE twice identically (:49/:51) — harmless dup, do not "fix" by renaming one site.
**Probe:** `grep -c 'ENTRYPOINT_FILE = ' gpt_engineer/core/default/paths.py` → 2 (duplicate declaration is real).
**Probe:** `tests/core/default/test_steps.py` fixture `factorial_entrypoint` shows prose + single ```sh block; TestGenCode entrypoint test asserts extraction succeeds despite surrounding "Irrelevant explanations".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "gen_entrypoint ENTRYPOINT_FILE run.sh regex", limit: 10 });
```

## Verdict
Adopt the join-all-fences extraction and shared constant for any "LLM writes bootstrap script" loop; adapt the default prompt wording; omit venv-specific assumptions if your env differs. Note: generated run.sh is executed with `bash run.sh`, so sh-compatible output is assumed.
