<!-- capsule-v2 -->
# StreamEvent SSE framing — how do you emit multi-line payloads over SSE without the client truncating them at the first blank line?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How must arbitrary string/JSON event data be wrapped, parsed back, and formatted for both the custom SSE protocol and the WXO/OpenAI-delta protocol?

## StreamEvent format/parse round-trip
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/agent_loop.py:148-267` (`StreamEvent.format_data`, `StreamEvent.parse`, `StreamEvent.format_event`, `StreamEvent.prepare_message`, `StreamEvent.format`).
**Signature:** `format_data(data_str: str) -> str`; `parse(formatted_str: str) -> 'StreamEvent'`; `format(self, format: OutputFormat = None, **kwargs) -> str`; `OutputFormat` enum = `wxo | default`.
**Data Shape:** `name: str`, `data: str`. DEFAULT emits `event: <name>\n` + one `data:` line per logical line + blank terminator; WXO emits `data: {json}\n\n` wrapping an OpenAI-style `thread.message.delta` envelope built by `prepare_message` (uuid `msg-*` id, thread_id, `langgraph-agent` model).

### Decisive source
```python
# Per the SSE spec, a blank line terminates the event, so multi-line
# ``data`` must split on newlines and prefix each line with ``data: ``
# (including empty lines). Without that, a body containing ``\n\n``
# (e.g. markdown with a blank line between heading and bullets) is
# truncated at the first blank line and the rest is dropped by the client.
data_lines = self.data.split("\n")
data_block = "\n".join(f"data: {line}" for line in data_lines)
return f"event: {self.name}\n{data_block}\n\n"
```
And the inverse (`parse`, :184-202): strip the trailing terminator first (`rstrip("\n")`) so no phantom empty data line; collect ALL `data:` lines preserving blanks (multi-line bodies); strip **exactly one** leading space after `data:` — per SSE spec it is syntactic, not content.

**Flow:** raw payload → `format_data` (not JSON → unchanged; JSON object with exactly one string-valued key → unwrap to that string; otherwise → fenced ```json pretty block) → `.format()` wraps → client → `StreamEvent.parse()` reconstructs `(name, data)`.
**Invariant:** every logical line of DEFAULT-mode data MUST carry the `data: ` prefix (empty lines included) or clients drop everything after the first `\n\n`; the earlier short-circuit that returned bare `self.data` for non-Answer events was removed deliberately — slash-command events need the wrapper too, else raw JSON glues to the next event. `prepare_message` JSON-encodes WXO data precisely so it can never contain a bare newline.
**Probe:** `tests/unit/test_stream_event_format.py:47-56` pins the multiline output BYTE-EXACTLY (`event: Answer\ndata: line one\ndata: \ndata: line three\n\n`) plus `parse` round-trip equality; :34-44 wraps custom named events and Answer events alike; :59-69 asserts `format=None` ≡ DEFAULT for non-answer events; :72-81 pins the WXO delta envelope.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "StreamEvent format parse SSE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-line `data: ` framing + exact-one-space parse rule + round-trip pair (they are the portable protocol contract); adopt the one-string-key JSON unwrap as a display nicety; adapt event names (`CodeAgent`, `Policy`, …) to your frontend; omit `format_event`'s legacy object-with-`.answer` branch unless you have the same historical payload shape. Direct tests pin the framing; no coverage gap.
