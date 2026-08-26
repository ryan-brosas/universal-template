<!-- capsule-v2 -->
# E2B executor surface — what does the hosted-sandbox adapter map (results, errors, lifecycle) and where do v1/v2 SDKs diverge?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How does `E2BExecutor` translate code_interpreter executions into CodeOutput — final answers, image results, error text — and how does it survive both SDK generations?

## Result-object translation
**Path/Symbol:** `src/smolagents/remote_executors.py:E2BExecutor` (:335-447; ctor v1/v2 fork :365-370, run_code_raise_errors :374-436, cleanup :438-447).
**Signature:** `E2BExecutor(additional_imports, logger, allow_pickle=False, **kwargs)`; `run_code_raise_errors(code) -> CodeOutput`; `cleanup()` kills sandbox.
**Data Shape:** `execution.logs.stdout` joined with newlines = logs; `execution.error{name,value,traceback}`; results scanned for main result then attribute ladder jpeg/png → chart,data,html,javascript,json,latex,markdown,pdf,svg,text.

### Decisive source
```python
# :388-392 — the exception channel carries control flow across the sandbox wall:
if execution.error:
    if execution.error.name == RemotePythonExecutor.FINAL_ANSWER_EXCEPTION:
        final_answer = self._deserialize_final_answer(execution.error.value, self.allow_pickle)
        return CodeOutput(output=final_answer, logs=execution_logs, is_final_answer=True)
# :412-418 — binary results ride base64 attributes and become PIL images host-side:
for attribute_name in ["jpeg", "png"]:
    img_data = getattr(result, attribute_name, None)
    if img_data is not None:
        decoded_bytes = base64.b64decode(img_data.encode("utf-8"))
        return CodeOutput(output=PIL.Image.open(BytesIO(decoded_bytes)), logs=execution_logs, is_final_answer=False)
```

**Flow:** Construction forks on `hasattr(Sandbox, "create")` — v2 classmethod vs v1 constructor — so one adapter spans SDK generations; packages install immediately after sandbox up (`install_packages(additional_imports)`). Execution maps the triple-channel protocol: logs accumulate regardless of outcome; an error whose NAME is FinalAnswerException deserializes `.value` into a successful final answer (everything else raises AgentError embedding logs+name+value+traceback); no error → first `is_main_result` result wins, images decoded before data types, else `(None, False)`. Cleanup is try-guarded best-effort with a del of the sandbox handle.
**Invariant:** Errors are DATA here: the executor must inspect `error.name` BEFORE deciding success/failure because FinalAnswerException is deliberately raised by patched tool code inside the sandbox (see remote-final-answer-patching). A port that treats any execution.error as failure makes every final answer an exception.
**Probe:** `tests/test_remote_executors.py::TestE2BExecutorUnit.test_e2b_executor_instantiation/:test_cleanup` (:91-151), `TestE2BExecutorIntegration.test_final_answer_patterns` (:190+, parametrized code shapes incl. bare-expression returns), `test_execute_image_output` twin (:292 Docker variant). Live (unit): FakeSandbox replaying error{name:"FinalAnswerException", value:'safe: 42'} → is_final_answer True.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "E2BExecutor run_code_raise_errors is_main_result Sandbox.create", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-channel mapping (logs / error-name routing / typed result ladder) for any hosted interpreter. Adapt the attribute ladder to your runtime's rich-output set. Omit the v1 fork only when you pin a minimum SDK version.
