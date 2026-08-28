<!-- capsule-v2 -->
# HF chat template + custom_prompt interiors — how messages become a provider prompt string for text-completion-native models

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** When `prompt_factory` falls through to the HuggingFace path, where does the chat template come from, how is it rendered safely, and what is the bos/eos state machine of the role-dict `custom_prompt` fallback?

## hf_chat_template — template acquisition + sandboxed render
**Path/Symbol:** `litellm/litellm_core_utils/prompt_templates/factory.py` — `hf_chat_template` (:579-603), `ahf_chat_template` (:552-576, async twin sharing the same renderer), `_fetch_and_extract_template` (:498-549) / `_afetch_and_extract_template` (:444-495), `_render_chat_template` (:368-441); fetchers in `litellm/litellm_core_utils/prompt_templates/huggingface_template_handler.py` (whole file, :1-145): `_get_tokenizer_config` / `_aget_tokenizer_config`, `_get_chat_template_file` / `_aget_chat_template_file`, `_extract_token_value` (:131-145), `strftime_now` (:12-22).
**Signature:** `hf_chat_template(model: str, messages: list, chat_template: str | None = None) -> str`.
**Data Shape:** `model` is an HF repo id (e.g. `openai/gpt-oss-120b`); explicit `chat_template` string skips all fetching; fetches hit `https://huggingface.co/{model}/raw/main/tokenizer_config.json` and `chat_template.jinja[2]`; process-lifetime memo cache `litellm.known_tokenizer_config`.

### Decisive source
```python
# factory.py:513-547 (abridged) — memoization caches FAILURES too
if model in litellm.known_tokenizer_config:
    tokenizer_config = litellm.known_tokenizer_config[model]
else:
    tokenizer_config = get_config_fn(hf_model_name=model)
    litellm.known_tokenizer_config.update({model: tokenizer_config})
# priority: tokenizer_config["chat_template"] > chat_template.jinja > chat_template.jinja2
...
else:
    raise Exception("No chat template found")
```

**Flow:** (1) if no explicit template: fetch tokenizer_config.json (memoized per model for the process lifetime — including `{"status": "failure"}` on 404, so a missing config is fetched at most once per process); (2) template priority: `tokenizer_config["chat_template"]` > `chat_template.jinja` > `chat_template.jinja2` file; both file attempts fail → raise "No chat template found"; (3) bos/eos extracted via `_extract_token_value` which tolerates `str | {"content": ...} | None` shapes; (4) render in a jinja2 `ImmutableSandboxedEnvironment` with only two injected globals (`raise_exception`, `strftime_now`) — templates cannot touch Python objects.
**Invariant:** The sandbox is load-bearing: chat templates are untrusted remote content, so rendering must stay inside `ImmutableSandboxedEnvironment` with a closed global set. Failure memoization means a transient 404 poisons the model for the whole process — a deliberate availability trade-off to avoid hammering HuggingFace.
**Probe:** direct test `tests/llm_translation/test_prompt_factory.py::test_hf_chat_template` (:1305-1354) BLOCKED this pass by missing `vcr` at conftest import (re-observed live); adjacent runnable suite `tests/test_litellm/litellm_core_utils/prompt_templates/test_litellm_core_utils_prompt_templates_factory.py` re-executed live at the pin → 97 passed.

## _render_chat_template — system detection + alternation repair
**Path/Symbol:** `litellm/litellm_core_utils/prompt_templates/factory.py` — `_render_chat_template` (:368-441).
**Signature:** `_render_chat_template(env, chat_template: str, bos_token: str, eos_token: str, messages: list) -> str`.

### Decisive source
```python
# factory.py:387-398 — system support detected by TRIAL RENDERING
def _is_system_in_template():
    try:
        template.render(messages=[{"role": "system", "content": "test"}], eos_token="<eos>", bos_token="<bos>")
        return True
    except Exception:
        return False
...
# factory.py:426-435 (abridged) — alternation repair
if "Conversation roles must alternate user/assistant" in str(e):
    new_messages = []
    for i in range(len(reformatted_messages) - 1):
        new_messages.append(reformatted_messages[i])
        if reformatted_messages[i]["role"] == reformatted_messages[i + 1]["role"]:
            if reformatted_messages[i]["role"] == "user":
                new_messages.append({"role": "assistant", "content": ""})
            else:
                new_messages.append({"role": "user", "content": ""})
```

**Flow:** (1) trial-render a fake system message — if it raises, the template has no system slot and every system message is rewritten to `user`; (2) render with `add_generation_prompt=True`; (3) if the template demands strict user/assistant alternation and errors on consecutive same-role messages, insert EMPTY messages of the opposite role between them and re-render. All render failures are wrapped as `Error rendering template - {e}` (the caller's `prompt_factory` then falls back to `default_pt`).
**Invariant:** Detection is behavioral (trial render), not string-matching on the template — porting this as a regex over the jinja source breaks on any template that handles system conditionally. The empty-message insertion must preserve order and append the final message after the loop.
**Probe:** covered by the 97-passed factory unit suite (live); no separate direct test for the repair path exists outside the vcr-blocked llm_translation suite.

## custom_prompt — the role-dict bos/eos state machine
**Path/Symbol:** `litellm/litellm_core_utils/prompt_templates/factory.py` — `custom_prompt` (:5216-5255); consumed by every role-dict prompt function in the file (e.g. `alpaca_pt` :125, `llama_2_chat_pt` :146, `mistral_instruct_pt` :285) and by `response_schema_prompt` (:5176-5199) via `litellm.custom_prompt_dict` overrides.
**Signature:** `custom_prompt(role_dict: dict, messages: list, initial_prompt_value: str = "", final_prompt_value: str = "", bos_token: str = "", eos_token: str = "") -> str`.
**Data Shape:** `role_dict[role] = {"pre_message": str, "post_message": str}`; either key may be absent (→ ""); message content may be a str or a list of blocks (only `text` parts are concatenated).

### Decisive source
```python
# factory.py:5224-5252 (abridged)
prompt = bos_token + initial_prompt_value
bos_open = True
## a bos token is at the start of a system / human message
## an eos token is at the end of the assistant response to the message
for message in messages:
    role = message["role"]
    if role in ["system", "human"] and not bos_open:
        prompt += bos_token
        bos_open = True
    pre_message_str = role_dict[role]["pre_message"] if role in role_dict and "pre_message" in role_dict[role] else ""
    post_message_str = role_dict[role]["post_message"] if role in role_dict and "post_message" in role_dict[role] else ""
    ...
    if role == "assistant":
        prompt += eos_token
        bos_open = False
prompt += final_prompt_value
```

**Flow:** single pass with one boolean (`bos_open`): a bos token is prepended whenever a system/human message follows an assistant turn (i.e. a new conversation turn opens); each message is wrapped in its role's pre/post strings; every assistant message closes with eos; the result is `bos + initial + <wrapped turns> + final`.
**Invariant:** The state machine keys off ROLE NAMES `"system"`/`"human"`/`"assistant"` — callers must normalize OpenAI `user`→`human` before calling (the role-dict prompt functions do this upstream). Missing role entries degrade to bare content, never KeyError.
**Probe:** no runnable direct test exists this session (the llm_translation suite is vcr-blocked); behavior confirmed by full source read of :5216-5255 plus the 97-passed factory unit suite (live) which exercises the role-dict prompt functions built on it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "hf_chat_template _render_chat_template custom_prompt known_tokenizer_config",
  filePattern: "factory.py", limit: 20 });
// → rank-1..n surface hf_chat_template :579, _render_chat_template :368, _fetch_and_extract_template :498, custom_prompt :5216
```

## Verdict
Adopt the three-tier template acquisition (explicit arg > tokenizer_config.json > .jinja file) with failure memoization, the sandboxed-environment render with closed globals, behavioral system-slot detection, and the empty-message alternation repair; adopt the one-flag bos/eos state machine for role-dict prompts. Adapt the HuggingFace URLs to your template registry, and the memo cache to a TTL'd store if you cannot accept process-lifetime failure poisoning. Omit the Together-AI legacy flow (commented out at :665-680) and the per-provider prompt functions unless you port those providers verbatim. Coverage caveat: the only direct `hf_chat_template` test (llm_translation/test_prompt_factory.py:1305) is vcr-blocked in this environment; evidence is source read + the 97-passed adjacent unit suite.
