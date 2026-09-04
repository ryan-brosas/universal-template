<!-- capsule-v2 -->
# LLM.call unsupported-'stop' retry — string-sniffed capability ladder with persistent drop_params memory

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does crewAI recover from providers that reject the `stop` parameter — and why is the recovery keyed off error TEXT rather than a typed exception?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/llm.py` — `LLM.call` except-arm (:1914-1957), mirrored in `acall` (:2046+).
**Signature:** `call(messages, tools=None, callbacks=None, available_functions=None, from_task=None, from_agent=None, response_model=None) -> str | Any`.
**Data Shape:** `self.additional_params: dict` mutates across retries (`additional_drop_params: list[str]`) — the failed param name becomes permanent state on the instance.

### Decisive source
```python
# :1909 context-window errors are NOT retried here — the executor owns them
except LLMContextLengthExceededError:
    # "handled by CrewAgentExecutor._invoke_loop ... summarize or abort
    #  based on respect_context_window"
    raise
except Exception as e:
    error_str = str(e)
    unsupported_stop = "'stop'" in error_str and (
        "Unsupported parameter" in error_str
        or "does not support parameters" in error_str)
    if unsupported_stop:
        if ("additional_drop_params" in self.additional_params
            and isinstance(self.additional_params["additional_drop_params"], list)):
            self.additional_params["additional_drop_params"].append("stop")  # :1928
        else:
            self.additional_params = {"additional_drop_params": ["stop"]}
        logging.info("Retrying LLM call without the unsupported 'stop'")
        return self.call(messages, tools=tools, ...)   # full recursive retry
    crewai_event_bus.emit(self, event=LLMCallFailedEvent(error=str(e), ...))
    raise
```

**Flow:** call → emit started → validate params → o1 models get system-role messages demoted to assistant (:1870) → prepare/stream-or-not → on generic failure sniff `str(e)` for stop-parameter rejection → append "stop" to `additional_drop_params` (merging into an existing list) → recurse once; next attempt's completion params omit it → any other failure emits LLMCallFailedEvent (with current call_id) and re-raises.
**Invariant:** The recursion terminates because after the first mutation the provider no longer sees `stop`; but the sniff is brittle BY DESIGN — LiteLLM wraps heterogeneous SDKs so no shared exception type exists. A porter adding typed handling must keep the LLMContextLengthExceededError re-raise FIRST or the agent's summarize-vs-abort decision gets swallowed. Note upstream ships these two tests skipped ("Highly flaky on ci") — the contract lives in source + caplog assertion text.
**Probe:** `grep -cF "Retrying LLM call without the unsupported 'stop'" lib/crewai/src/crewai/llm.py` → `2` (sync + async arms); `grep -c 'additional_drop_params' lib/crewai/src/crewai/llm.py` → `8`.
**Direct test:** `tests/test_llm.py::test_llm_call_when_stop_is_unsupported` (:643, asserts the exact log line) — UPSTREAM-SKIPPED caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "LLM.call high-level LLM call method stop parameter retry", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.llm.LLM.call Method 1820-1957
```

## Verdict
Adopt the mutate-then-recurse recovery pattern for cross-provider parameter incompatibilities. Adapt the sniff strings to your gateway's error corpus. Omit litellm wiring and native-provider routing (`_get_native_provider` ladder).
