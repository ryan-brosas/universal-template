<!-- capsule-v2 -->
# Token-window report — how do you show context usage without ever crashing on an unknown tokenizer?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does an observability command decompose a chat's context window into actionable rows, price images, and grade remaining budget — while failing open on tokenizer errors?

## Decomposition rows + three-way remaining ladder
**Path/Symbol:** `aider/commands.py`: `Commands.cmd_tokens` (:445-551); `aider/models.py`: `Model.token_count_for_image` (:672-701), `Model.token_count` fail-open (:666-670).
**Signature:** `cmd_tokens(self, args)`; `token_count_for_image(self, fname) -> int`; rows are `(tokens:int, label:str, tip:str)` tuples.
**Data Shape:** per-row cost = tokens × (`info["input_cost_per_token"] or 0`); limit = `info["max_input_tokens"] or 0`.

### Decisive source
```python
limit = self.coder.main_model.info.get("max_input_tokens") or 0
if not limit:
    return
remaining = limit - total
if remaining > 1024:
    self.io.tool_output(f"...{fmt(remaining)} tokens remaining in context window")
elif remaining > 0:
    self.io.tool_error(f"...(use /drop or /clear to make space)")
else:
    self.io.tool_error(f"...window exhausted (use /drop or /clear to make space)")
```
```python
# models.py — observability fails OPEN, never crashes the report
try:
    return len(self.tokenizer(msgs))
except Exception as err:
    print(f"Unable to count tokens: {err}")
    return 0
```

**Flow:** rows are appended in fixed order — system messages (fmt_system_prompt of main_system + system_reminder), chat history (done+cur), repository map (**recomputed live** via `repo_map.get_repo_map(chat_files, other_files)`, not a cached value), then per-file rows where images use tile arithmetic and text is fence-wrapped. File rows sort by token count (tuple sort), each prints its cost, then a total row and the ladder above.
**Invariant:** a reporter must never raise on unknown models — `token_count` returns 0 on any tokenizer failure; unknown context limit exits silently rather than guessing.
**Probe:** direct test: `tests/basic/test_commands.py::test_cmd_tokens_output` (:524, executed via `-k test_cmd_tokens_output`, **26 passed** suite run this pass). Image math (models.py :683-700): long side clamped to 2048 proportionally, short side scaled to ≥768, `ceil(dim/512)` tiles ×170 + 85 base — pure function of dimensions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "token_count_for_image", limit: 5 });
// total:1 rank-1: aider.aider.models.Model.token_count_for_image aider/models.py 672-701
```

## Verdict
Adopt the row decomposition (system/history/map/files), live repo-map recomputation for honest "what would be sent" numbers, the 1024-token warn threshold ladder, and the fail-open tokenizer contract. Adapt OpenAI's 2048/768/512×170+85 constants if your provider prices images differently; omit cost columns when your metadata lacks per-token pricing.
