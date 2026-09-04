<!-- capsule-v2 -->
# Tool-call INVALID_JSON envelope — how do malformed model tool arguments survive round-trips instead of crashing the request?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What happens when a model emits tool-call arguments that aren't valid JSON or aren't an object, and how must they be rendered back to provider APIs that demand objects?

## `BaseToolCallPart.args_as_dict` / `args_as_json_str` + `INVALID_JSON_KEY`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:INVALID_JSON_KEY = 'INVALID_JSON'` (:35–39, value recommended by Anthropic docs), `BaseToolCallPart.args_as_dict(raise_if_invalid=False)` (:2209–2233), `args_as_json_str()` (:2235–2259).
**Signature:** `args_as_dict(self, *, raise_if_invalid: bool = False) -> dict[str, Any]`; `args_as_json_str(self) -> str`.
**Data Shape:** `args: str | dict | None`. Malformed/non-object JSON degrades to `{INVALID_JSON_KEY: '<raw args>'}` (dict form) or `'{"INVALID_JSON":"<raw args>"}'` (string form) instead of raising — unless `raise_if_invalid=True`.

### Decisive source
```python
# messages.py:2249-2259 — verbatim passthrough when bytes are object JSON; re-serialize otherwise
def args_as_json_str(self):
    if not self.args:
        return '{}'
    if isinstance(self.args, str):
        try:
            if isinstance(pydantic_core.from_json(self.args), dict):
                # Returned verbatim rather than re-serialized, as the exact bytes the model
                # produced (key order, whitespace) matter for prompt caching.
                return self.args
        except ValueError:
            pass
    return pydantic_core.to_json(self.args_as_dict()).decode()
```

**Flow:** model args arrive as string or dict → consumers needing dicts call `args_as_dict`: empty/None → `{}`, dict → identity, str → parse; parse failure or non-object assert → either raise (`raise_if_invalid=True`, e.g. capability-id extraction) or wrap under `INVALID_JSON_KEY` so a retry-flow request can still be built. String rendering prefers VERBATIM bytes when they already are object JSON; only wrapped/repaired args get re-serialized.

**Invariant:** The specific string `'INVALID_JSON'` is what Anthropic's docs recommend for this situation — don't rename it. Verbatim byte fidelity is load-bearing for prompt caching: re-serializing valid-but-unusual key order/whitespace would move the cached prefix. Conversely this is NOT the way to render still-streaming args: a partial fragment that would become valid JSON once later deltas concatenate gets degraded to the wrapper — UI event streams must emit streaming fragments verbatim. Empty/None args render as `{}`/`'{}'`.

**Probe:** `tests/test_messages.py` pins both degrade modes and the verbatim-vs-reserialized fork of `args_as_json_str`; `tests/test_models.py`-adjacent retry tests exercise the envelope surviving into a rebuilt request.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "args_as_dict args_as_json_str INVALID_JSON_KEY BaseToolCallPart", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the graceful-degrade envelope keyed on the Anthropic-recommended sentinel and the verbatim-byte passthrough for caching stability. Adapt the raise/degrade split points to your call sites (history repair wants degrade; strict extraction wants raise). Omit nothing.
