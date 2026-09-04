<!-- capsule-v2 -->
# Offline model fakes — how do you exercise a translator or model client end-to-end with ZERO network?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How do the upstream Python tests drive the full translate→validate→repair loop and the HTTP client without a real LLM endpoint, and what injection contract does that reveal?

## Fake 1 — the model interface: subclass and override complete()
**Path/Symbol:** `python/tests/test_translator.py:11-31` (`FixedModel`, whole class; conversation capture at :22-31).
**Signature:** `class FixedModel(typechat.TypeChatLanguageModel)` with `responses: Iterator[str]`; `@override async def complete(self, prompt: str | list[typechat.PromptSection]) -> typechat.Result[str]`.

### Decisive source
```py
# Capture a snapshot because the translator
# can choose to pass in the same underlying list.
if isinstance(prompt, list):
    prompt = prompt.copy()

self.conversation.append({ "kind": "CLIENT REQUEST", "payload": prompt })
response = next(self.responses)
self.conversation.append({ "kind": "MODEL RESPONSE", "payload": response })
return typechat.Success(response)
```
**Flow:** tests hand the fake an ordered script of raw model outputs (valid JSON, schema-violating JSON, malformed JSON) → run the real `TypeChatJsonTranslator.translate` under `asyncio.run` → assert the ENTIRE recorded conversation against a syrupy snapshot (`assert m.conversation == snapshot`). No mock of the translator, validator, or prompts — only the network edge is faked, so prompt wording, repair-turn construction, and Result plumbing are all exercised for real.
**Invariant:** two easy-to-miss details. (1) The shallow `prompt.copy()` guard is load-bearing: the translator may re-pass THE SAME list object on the repair turn, so without the copy the recorded first request would mutate retroactively and the snapshot would lie about what was sent. (2) `next(self.responses)` raises StopIteration if the loop retries more than scripted — the fake doubles as a retry-count tripwire.

## Fake 2 — the transport attribute: swap _async_client for MockTransport
**Path/Symbol:** `python/tests/test_model.py:15-28` (`_MockHttpxLanguageModel.use_mock_transport` :16-17; `_make_model` :20-28), payload helper `_completion_payload` :31-32.
**Signature:** `def use_mock_transport(self, handler: Callable[[httpx.Request], httpx.Response]) -> None: self._async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))`.

### Decisive source
```py
model = _MockHttpxLanguageModel(
    url="https://example.invalid/v1/chat/completions",
    headers={},
    default_params={"model": "gpt-test"},
)
# Route the model's requests through a mock transport instead of the network.
model.use_mock_transport(handler)
```
**Flow:** construct the REAL `HttpxLanguageModel` (its eager client from `model.py:67` is simply replaced), then swap the private `_async_client` attribute for a MockTransport-backed client whose handler returns canned `{"choices":[{"message":{"role":"assistant","content":...}}]}` payloads, oversized bodies, or streamed chunk sequences. All four size-limit DoS-hardening behaviors are pinned this way with zero sockets.
**Invariant:** the private `_async_client` attribute is the SANCTIONED transport seam (nothing else is touched to redirect traffic), and `.invalid` TLD + `max_response_bytes = 0` disable paths prove the suite can never accidentally dial out. Cross-port adjacency: TS reaches the same goal by stubbing global fetch instead (`typescript/tests/model.test.mjs` `setupFetch` :82-91 / `makeJsonResponse` :32-39 family) — port the ATTRIBUTE-swap idea to any client that owns its transport object.

**Probe (executed this pass):** provisioned `/tmp/tc-p3-run` (Python 3.14.7, pytest 8.4.2) OUTSIDE the read-only checkout via `pip install -e 'python[dev]'`; ran the repo-owned CI command `pytest -vv` from `python/`: **22 passed, 17 snapshots passed in 0.25s**, including all five FixedModel conversation snapshots and all four MockTransport size-limit tests. Conversation snapshots live in ONE amber file `python/tests/__snapshots__/test_translator.ambr` (386L, 5 whole-conversation fixtures) pinning byte-exact request/repair exchanges. Coverage check: test_translator.py, test_model.py, utilities.py = no_recorded_issue/metadata_match @gen 2026-08-25T19:58:29Z.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"FixedModel fake model translator test capture messages","limit":5}'
// rank1 Class FixedModel test_translator.py :11-31 (callers 5); rank2-3 __init__/complete;
// also rank-visible: _MockHttpxLanguageModel.use_mock_transport test_model.py :16-17.
// CAVEAT: trace_path inbound use_mock_transport resolves callers_total=0 — its sole real caller
// (_make_model :27) is confirmed by direct read, not by graph edges.
```

## Verdict
Adopt both seams as the testing contract when porting: fake ONLY the model interface for loop/prompt/repair behavior, fake ONLY the transport attribute for wire/size/status behavior — never mock the translator internals. Adapt the fake mechanics to the host language (iterator script → generator, MockTransport → host HTTP test adapter); adapt the amber snapshot to your runner's snapshot format but keep WHOLE-conversation assertions so repair turns stay pinned. Omit nothing here — the shallow-copy guard and StopIteration tripwire are cheap and each caught a real failure mode upstream.
