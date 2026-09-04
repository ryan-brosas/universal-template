<!-- capsule-v2 -->
# gen-code-parse-contract — How does a one-shot LLM answer become an executable multi-file workspace?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What exact parsing contract turns the model's markdown answer into FilesDict without losing or corrupting files?

## Chat-to-files parse seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:gen_code` (:121-150) + `gpt_engineer/core/chat_to_files.py:chat_to_files_dict` (:38-66).
**Signature:** `gen_code(ai: AI, prompt: Prompt, memory: BaseMemory, preprompts_holder: PrepromptsHolder) -> FilesDict`; `chat_to_files_dict(chat: str) -> FilesDict`.
**Data Shape:** Input = full model transcript (`messages[-1].content`); output = flat dict {relative_path_str: file_body_str}. Path keys are cleaned strings; values are stripped code bodies.

### Decisive source
```python
# chat_to_files.py:49-64 — one regex drives everything
regex = r"(\S+)\n\s*```[^\n]*\n(.+?)```"
matches = re.finditer(regex, chat, re.DOTALL)
files_dict = FilesDict()
for match in matches:
    path = re.sub(r'[\:<>\"|?*]', "", match.group(1))   # strip illegal FS chars
    path = re.sub(r"^\[(.*)\]$", r"\1", path)            # unwrap [brackets]
    path = re.sub(r"^`(.*)`$", r"\1", path)              # unwrap backticks
    path = re.sub(r"[\]\:]$", "", path)                  # strip trailing ] or :
    files_dict[path.strip()] = content.strip()
```

**Flow:** system prompt (roadmap + generate w/ FILE_FORMAT injected + philosophy) → `ai.start(...)` → take LAST message only → `memory.log(CODE_GEN_LOG_FILE, ...)` full transcript → regex-scan for `PATH\n```lang\nBODY``` ` pairs → clean path → FilesDict.
**Invariant:** (1) Only `messages[-1].content` is parsed — earlier messages never contribute files. (2) Path-cleaning order matters: illegal chars first, then bracket/backtick unwraps anchored `^...$`, so `` `src/x.py`: `` becomes `src/x.py`. (3) The fence language tag (` ```python `) is consumed by `[^\n]*` — bodies never contain it. (4) Duplicate paths: later match overwrites earlier (plain dict set). The preprompt `file_format` trains the model to emit exactly this shape ("FILENAME\n```\nCODE\n```") — parser and prompt are ONE contract; porting either without the other breaks generation.
**Probe:** `grep -c 're.sub' gpt_engineer/core/chat_to_files.py` → 4 (the cleaning ladder); direct test `tests/core/default/test_steps.py::TestGenCode::test_generates_code_using_ai_model` parses the factorial fixture and asserts `len(code) == 2` (two files recovered).
**Probe:** `grep -n 'FILENAME' gpt_engineer/preprompts/file_format` → representation spec lines exist (parser-side counterpart of the contract).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "chat_to_files_dict gen_code FilesDict", limit: 10 });
```

## Verdict
Adopt the regex+cleaning ladder and last-message rule verbatim (pure string logic); adapt the fence grammar only if your own system prompt teaches a different file shape (keep prompt/parser paired); omit RudderStack logging around it. Coverage caveat: parse_partial on docs/ramblings fixtures does NOT touch this seam.
