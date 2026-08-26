<!-- capsule-v2 -->
# Azure structured-LLM assistant-keyword rewrite — why does every prompt's last message get "assistant" replaced with "ai" before the call?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does the Azure structured LLM avoid a content-filter false positive without mutating caller state or breaking multimodal content?

## Connected graph-selected seam
**Path/Symbol:** `mem0/llms/azure_openai_structured.py`: `_rewrite_assistant_keyword` (staticmethod, :106-123) called first in `generate_response` (:74); auth ladder in `__init__` (:31-39).
**Signature:** `_rewrite_assistant_keyword(messages: List[Dict]) -> List[Dict]` — deep-copied input, last message's STRING content rewritten.
**Data Shape:** OpenAI chat messages; content may be str OR multimodal list-of-parts — only str is touched.

### Decisive source
```python
# Azure's content management policy can flag the literal word "assistant",
# which makes `add` fail (see issue #2636). The rewrite targets that
# trigger without mutating the caller's messages and without assuming the
# content is a string, so multimodal (list) content passes through untouched.
messages = copy.deepcopy(messages)
last_content = messages[-1].get("content")
if isinstance(last_content, str):
    messages[-1]["content"] = last_content.replace("assistant", "ai")
```

**Flow:** generate_response → rewrite (deepcopy → replace in final user turn) → reasoning-model param gate (`_is_reasoning_model` skips temperature/top_p; max_completion_tokens vs max_tokens rename; optional reasoning_effort) → plain `chat.completions.create` (NOT beta.parse like the OpenAI twin) → tool-call responses parsed through `extract_json` brace-slice salvage before json.loads.
**Invariant:** the rewrite is copy-on-write (caller's list is never aliased), string-only (multimodal part lists pass through), and LAST-MESSAGE-ONLY; it exists because Azure's Indirect Attacks filter flags the literal word "assistant" and fails memory extraction outright (#2636) — a naive port that mutates in place corrupts caller-owned history, and one that rewrites all messages wastes tokens and risks flagging other roles. Auth falls back to DefaultAzureCredential + bearer-token provider when api_key is missing/empty/the literal placeholder "your-api-key".
**Probe:** `grep -n 'replace("assistant", "ai")' mem0/llms/azure_openai_structured.py` (exactly :122); `grep -n "your-api-key" mem0/llms/azure_openai_structured.py`.
**Direct test:** no dedicated suite at this pin for the staticmethod itself — behavior pinned by source docstring + issue reference #2636; sibling non-structured `azure_openai.py` carries the identical helper (:74-91), confirming pattern intent. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_rewrite_assistant_keyword AzureOpenAIStructuredLLM", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the copy-on-write, string-only, last-message keyword rewrite whenever targeting Azure content filtering; adapt the trigger word to the deployed filter policy; omitting the deepcopy or isinstance guard introduces aliasing/crash bugs. Direct-test caveat recorded (staticmethod untested upstream; helper duplicated in azure_openai.py).
