<!-- capsule-v2 -->
# Prompt-function service dispatch — after a prompt renders, how does the function pick which client method to call?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** A prompt function can run against chat, text, image, or audio services — what is the exact order of render → select → dispatch, and why does streaming narrow the selectable services?

## Render under filters, then select with a streaming-restricted type tuple, then isinstance-dispatch
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_prompt.py:KernelFunctionFromPrompt._render_prompt` (270–299), `._invoke_internal` (170–241), `._invoke_internal_stream` (243–270), `._inner_render_prompt` (301–304).
**Signature:** `async def _render_prompt(self, context: FunctionInvocationContext, is_streaming: bool = False) -> PromptRenderingResult`.
**Data Shape:** PromptRenderingResult carries rendered_prompt, the selected ai_service, its converted execution_settings, and an optional short-circuit function_result. The four client bases are ChatCompletionClientBase / TextCompletionClientBase / TextToImageClientBase / TextToAudioClientBase.

### Decisive source
```python
async def _render_prompt(self, context, is_streaming=False):
    self.update_arguments_with_defaults(context.arguments)
    _rebuild_prompt_render_context()
    prompt_render_context = PromptRenderContext(function=self, kernel=..., arguments=..., is_streaming=is_streaming)
    stack = context.kernel.construct_call_stack(
        filter_type=FilterTypes.PROMPT_RENDERING, inner_function=self._inner_render_prompt)
    await stack(prompt_render_context)                    # 1. render INSIDE the filter onion
    if prompt_render_context.rendered_prompt is None:
        raise PromptRenderingException("Prompt rendering failed, no rendered prompt was returned.")
    selected_service = context.kernel.select_ai_service(  # 2. select AFTER rendering
        function=self, arguments=context.arguments,
        type=(TextCompletionClientBase, ChatCompletionClientBase) if prompt_render_context.is_streaming else None)
    return PromptRenderingResult(rendered_prompt=..., ai_service=selected_service[0],
                                 execution_settings=selected_service[1], function_result=...)

# _invoke_internal: isinstance ladder over the four bases; _invoke_internal_stream: only two
if isinstance(prompt_render_result.ai_service, TextCompletionClientBase): ...
else:
    raise FunctionExecutionException(f"Service `{type(...)}` is not a valid AI service")
```

**Flow:** fill missing input variables with defaults → build the PROMPT_RENDERING filter stack over `_inner_render_prompt` (the filter onion's second application site — a filter may rewrite rendered_prompt after `next`) → a None rendered_prompt is fatal before any selection → select the service with a type tuple that DEPENDS on the mode: streaming passes only (Text, Chat) because image/audio clients have no stream methods, non-streaming passes None (the default four-base tuple) → dispatch by isinstance ladder to the matching client method, passing kernel+arguments through for chat. Every provider exception is wrapped in `FunctionExecutionException(f"Error occurred while invoking function {name}: {exc}")`; an empty chat completion list is also wrapped ("No completions returned").
**Invariant:** selection happens AFTER rendering completes, so a prompt-rendering filter that swaps the prompt cannot change which service was chosen mid-flight — but it CAN change the settings-visible state via context.arguments. Streaming must never reach an image/audio service: the restriction lives in the SELECT call (type tuple), not in the dispatch ladder, so the failure surfaces as "No service found" rather than a runtime AttributeError.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_prompt.py::test_prompt_render_with_filter` (369–394: a prompt_rendering filter rewrites rendered_prompt post-`next` to "preface test", proving render-inside-onion ordering); `::test_invoke_chat_stream` (152–178: same function object drives get_chat_message_contents AND get_streaming_chat_message_contents by mode); `::test_invoke_exception` (180–207: provider Exception wrapped in FunctionExecutionException in both modes); `::test_invoke_text` (209–231: text base dispatches get_text_contents/get_streaming_text_contents).
**Coverage caveat:** Codebase Memory MCP not connected this session; direct source+test reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_render_prompt select_ai_service is_streaming PROMPT_RENDERING construct_call_stack", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the render→select→dispatch order with the mode-dependent type tuple: capability restrictions belong at selection time so they fail with a clean "no service" error. Adapt the isinstance ladder to your host's client hierarchy (a registry keyed by capability would be the cleaner generalization). Omit nothing from the error wrapping: prompt functions are model-facing, so provider failures must arrive as FunctionExecutionException carrying the function name, never as raw provider SDK exceptions.
