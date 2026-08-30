<!-- capsule-v2 -->
# ai-collapse-vision-ladder — When are consecutive messages collapsed before inference, and how is model capability detected?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What triggers message collapsing, what is the vision-detection ladder, and which provider branches exist?

## AI wrapper seam
**Path/Symbol:** `gpt_engineer/core/ai.py:AI.__init__` (:88-118 vision ladder), `_collapse_text_messages` (:165-204), `next` (:206-251), `_create_chat_model` (:330-379), `backoff_inference` (:253-287).
**Signature:** `next(messages, prompt=None, *, step_name) -> List[Message]`; `start(system, user, *, step_name)` delegates to next().
**Data Shape:** Langchain message objects; content may be str OR list-of-parts for vision.

### Decisive source
```python
self.vision = (
    ("vision-preview" in model_name)
    or ("gpt-4-turbo" in model_name and "preview" not in model_name)
    or ("claude" in model_name)
)
...
# inside next():
if not self.vision:
    messages = self._collapse_text_messages(messages)
response = self.backoff_inference(messages)
self.token_usage_log.update_log(messages=messages, answer=response.content, step_name=step_name)
messages.append(response)
```
```python
def _create_chat_model(self):
    if self.azure_endpoint: return AzureChatOpenAI(... deployment_name=self.model_name ...)
    elif "claude" in self.model_name: return ChatAnthropic(... max_tokens_to_sample=4096 ...)
    elif self.vision: return ChatOpenAI(... max_tokens=4096 ...)   # vision models default low limits
    else: return ChatOpenAI(...)
```

**Flow:** constructor sniffs model name → per-call: optional prompt append → collapse consecutive same-role messages UNLESS vision → backoff inference (expo, RateLimitError, max_tries=7, max_time=45) → token log update → append AIMessage.
**Invariant:** (1) Collapsing JOINS same-type neighbors with "\n\n" — this is why improve_fn's TWO HumanMessages (files then prompt) reach the model as one blob on non-vision models but stay separate on vision ones; ordering still preserved. (2) Vision detection is NAME-SUBSTRING based with the counter-intuitive arm: bare "gpt-4-turbo" ⇒ vision, "-preview" suffixed ⇒ NOT. (3) Vision branch caps max_tokens=4096 explicitly ("vision models default to low max token limits") — omitting this truncates code output. (4) backoff decorator targets openai.RateLimitError only — Anthropic rate limits surface as unhandled. (5) ClipboardAI overrides next() entirely: serializes to clipboard/file, reads human-pasted reply — proving next() IS the LLM seam (everything else is plumbing).
**Probe:** `grep -n 'vision-preview' gpt_engineer/core/ai.py` → :111 (ladder first arm).
**Probe:** `grep -c 'StreamingStdOutCallbackHandler()' gpt_engineer/core/ai.py` → 4 (one per provider branch incl azure).
**Probe:** `grep -n 'max_tries=7' gpt_engineer/core/ai.py` → :253 decorator line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "_collapse_text_messages vision _create_chat_model backoff_inference", limit: 10 });
```

## Verdict
Adopt collapse-before-send for token economy and the substring vision ladder as a provider-routing pattern; adapt provider branches to your SDK set; keep the explicit vision max_tokens override. serialize/deserialize_messages roundtrip forces is_chunk=False on load — carry if persisting transcripts.
