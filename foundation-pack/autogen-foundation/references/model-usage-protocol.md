<!-- capsule-v2 -->
# Model usage protocol — what minimal contract ties token accounting between clients and budget consumers?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** Which two methods must every model client expose so context budgeting can be computed client-independently?

## RequestUsage dataclass + count_tokens/remaining_tokens pair
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/models/_types.py` `RequestUsage` :85–88, `CreateResult` :107–122; `python/packages/autogen-core/src/autogen_core/models/_model_client.py` `ChatCompletionClient.count_tokens` :281, `remaining_tokens` :284; reference impl `python/packages/autogen-ext/src/autogen_ext/models/openai/_openai_client.py` :1151–1163.
**Signature:** `count_tokens(messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int` · `remaining_tokens(same) -> int` · `RequestUsage(prompt_tokens: int, completion_tokens: int)`.
**Data Shape:** `CreateResult{finish_reason, content: str | List[FunctionCall], usage: RequestUsage, cached: bool}`; usage rides EVERY completion result, cached or not.

### Decisive source
```python
@dataclass
class RequestUsage:
    prompt_tokens: int
    completion_tokens: int
```
```python
# ChatCompletionClient (both @abstractmethod, core protocol):
def count_tokens(self, messages, *, tools = []) -> int: ...
def remaining_tokens(self, messages, *, tools = []) -> int: ...

# OpenAI reference implementation — remaining derives from limit minus count:
def remaining_tokens(self, messages, *, tools = []) -> int:
    token_limit = _model_info.get_token_limit(self._create_args["model"])
    return token_limit - self.count_tokens(messages, tools=tools)
```

**Flow:** every completion carries `usage` + `cached` flag → budget consumers call ONLY `count_tokens`/`remaining_tokens` on the abstract client (replay/cache/adapters pass through or reimplement per family) → negative `remaining_tokens` is meaningful output (drives eviction, see token-budget-middle-out capsule).
**Invariant:** usage is a plain dataclass — value-comparable and trivially serializable, no behavior; `remaining_tokens` MUST be allowed to go negative (callers depend on the sign); both methods accept the same `tools` argument because tool schemas consume context budget too; cache layers forward accounting unchanged (`ChatCompletionCache.remaining_tokens` delegates).
**Probe:** `python/packages/autogen-ext/tests/models/test_reply_chat_completion_client.py::test_token_count_logics` (:120–158) and `.../test_llama_cpp_model_client.py::test_count_and_remaining_tokens` (:151–163 — count/remaining agree with known token limits).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "RequestUsage remaining_tokens count_tokens", limit: 15 });
```

## Verdict
Adopt the two-method client protocol plus the ride-along usage dataclass for any multi-provider LLM layer. Adapt the tokenizer behind `count_tokens` per provider. Omit the deprecated `capabilities` fallback property (warns and forwards to `model_info`) unless you must support old clients.
