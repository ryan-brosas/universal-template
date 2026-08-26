<!-- capsule-v2 -->
# Weak-model commit-message ladder — degrading message generation across models under a token budget

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When commit messages come from cheaper models than the coder, how do you fall back across them without crashing on context overflow or mangling quoted output?

## Ordered model walk: budget-skip, first-non-empty-wins, matched-quote strip only
**Path/Symbol:** `aider/repo.py`: `GitRepo.get_commit_message(diffs, context, user_language=None)` (:326-373).
**Signature:** returns stripped message string or None; caller `commit()` substitutes "(no commit message provided)" (:269-270).
**Data Shape:** prompt = optional user context + "# Diffs:\n" + diffs; system = `self.commit_prompt or prompts.commit_system` `.format(language_instruction=...)`; per-model spinner text "Generating commit message with {model.name}".

### Decisive source
```python
for model in self.models:
    with WaitingSpinner(spinner_text):
        if model.system_prompt_prefix:
            current_system_content = model.system_prompt_prefix + "\n" + system_content
        else:
            current_system_content = system_content
        messages = [dict(role="system", content=current_system_content),
                    dict(role="user", content=content)]
        num_tokens = model.token_count(messages)
        max_tokens = model.info.get("max_input_tokens") or 0
        if max_tokens and num_tokens > max_tokens:
            continue                      # skip this model, try the next
        commit_message = model.simple_send_with_retries(messages)
        if commit_message:
            break
if not commit_message:
    self.io.tool_error("Failed to generate commit message!")
    return
commit_message = commit_message.strip()
if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
    commit_message = commit_message[1:-1].strip()
```

**Flow:** build shared prompt -> walk `self.models` in order -> prepend the model's own system_prompt_prefix if it has one -> SKIP (continue, never abort) any model whose `max_input_tokens` is set and exceeded -> first non-empty `simple_send_with_retries` result wins -> strip whitespace -> strip surrounding double quotes ONLY when BOTH edges quote -> else return None.
**Invariant:** an over-budget model is skipped, not fatal; unknown `max_input_tokens` (0/None) means "attempt anyway"; unmatched quotes survive untouched (a leading or lone quote is data, not wrapping); total failure is reported and returned as None so commit() still completes with its placeholder subject.
**Probe:** `tests/basic/test_repo.py` — `test_get_commit_message` (:132), `test_get_commit_message_strip_quotes` (:156), `test_get_commit_message_no_strip_unmatched_quotes` (:167), `test_get_commit_message_with_custom_prompt` (:178), `test_get_commit_message_uses_system_prompt_prefix` (:688). Executed GREEN this run (repo `.venv`). Anchors: `grep -nF 'num_tokens = model.token_count(messages)' aider/repo.py` -> :355; `grep -nF "commit_message[1:-1].strip()" aider/repo.py` -> :371.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_commit_message", limit: 4 });
// resolves GitRepo.get_commit_message :326-373 plus all four direct tests
```

## Verdict
Adopt the ordered weak-model walk with budget-skip semantics and the both-edges quote rule. Adapt model selection config and the system template; omit Aider's commit_prompt wording. Porters who strip quotes with `.strip('"')` will eat legitimate leading quotes — keep the paired-edge condition.