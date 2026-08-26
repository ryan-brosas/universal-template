<!-- capsule-v2 -->
# Text-completion provider degradation — how do you serve a chat-only model string through a completions endpoint?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** When `model_type="text"`, how must provider prefix, auth env vars, and prompt framing be rewritten so legacy completion APIs work with chat-style configs?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/lm.py:litellm_text_completion` (:132-155).
**Signature:** `def litellm_text_completion(request: str, cache={"no-cache": True, "no-store": True}) -> litellm response`.
**Data Shape:** Input kwargs carry chat-style `model="provider/model"` + `messages`; output is a text-completion response whose choices use `["text"]`, consumed by the shared extractor `c.message.content if hasattr(c, "message") else c["text"]` (lm.py:95-98).

### Decisive source
```python
model = kwargs.pop("model").split("/", 1)
provider, model = model[0] if len(model) > 1 else "openai", model[-1]
api_key  = kwargs.pop("api_key", None) or os.getenv(f"{provider}_API_KEY")
api_base = kwargs.pop("api_base", None) or os.getenv(f"{provider}_API_BASE")
prompt = "\n\n".join([x["content"] for x in kwargs.pop("messages")] + ["BEGIN RESPONSE:"])
return litellm.text_completion(
    cache=cache,
    model=f"text-completion-openai/{model}",   # provider rewritten to openai-compatible
    api_key=api_key, api_base=api_base, prompt=prompt, **kwargs,
)
```

**Flow:** Split `provider/model` → derive `{PROVIDER}_API_KEY`/`{PROVIDER}_API_BASE` env names → flatten messages into one prompt terminated by a literal `BEGIN RESPONSE:` sentinel → force the `text-completion-openai/` litellm provider prefix regardless of origin.
**Invariant:** (1) A bare model string (no slash) degrades to provider `openai`. (2) Explicit kwargs beat env vars (`pop(...) or os.getenv`). (3) The `BEGIN RESPONSE:` tail is part of the continuation contract — dropping it changes output framing. (4) Auth never lands in the history entry: `__call__` strips `api_*` keys before appending (:101, :258).
**Probe:** deterministic pin — source excerpt matches byte-exact at :136-155; the `c.message.content if hasattr(c, "message") else c["text"]` dual-shape extractor appears at lm.py:96 and :253 (verified by direct read this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "litellm_text_completion provider BEGIN RESPONSE", limit: 10 });
```

## Verdict
Adopt the provider-prefix rewrite + messages-flattening ladder for any completions-only backend; adapt the sentinel string and env-var naming; omit if your router handles text models natively. Related family quirks mined separately: Groq forces `temperature=1e-8` for 0 and drops logprobs (lm.py:652-662), Claude clamps `max_tokens=min(x,4096)` and retries only `(RateLimitError,)` max_tries=8 (:734, :803-810), Google pops forbidden `n` and hardcodes `candidate_count=1` (:1181, :1238-1239). Caveat: no upstream tests; source-pinned.
