<!-- capsule-v2 -->
# Logger-as-value trick — how do log lines become message content without a second append?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How are transcript entries rendered to console AND stored to history AND written to HTML in one expression?

## log() returns its input after printing/persisting
**Path/Symbol:** `os_computer_use/logging.py:74-82` (`Logger.log`), `:61-71` (`write_log_file`), `:33-46` (template load); call sites `sandbox_agent.py:189,199,208,214`.
**Signature:** `log(text, color="black", print=True) -> text` (same object returned).
**Data Shape:** Every entry appended as `{"text": str, "color": name}`; full file REWRITTEN from `self.logs` on every line via `{{content}}` placeholder replacement in the bundled `templates/log.html`.

### Decisive source
```python
def log(self, text, color="black", print=True):
    if print:
        self.print_colored(text, color)
    self.logs.append({"text": text, "color": color})
    if self.log_file:
        self.write_log_file(self.logs, self.log_file)
    return text
```
```python
# usage inside run(): the log side effect PRODUCES the message content
Message(logger.log(f"OBSERVATION: {result}", "yellow"))
Message(logger.log(f"THOUGHT: {self.append_screenshot()}", "green"))
```

**Flow:** call log() with formatted text → ANSI print (gray=37;2 dim) → append structured entry → rewrite whole HTML file (template swap on `{{content}}`) → return original string → caller wraps the RETURN VALUE in a Message.
**Invariant:** Logging is not a side channel but the value pipeline: console coloration, durable HTML transcript, and message construction happen in ONE expression, so history can never drift from what was displayed. Full-file rewrite each line is O(n²) by design — transcripts here are small; CSS colors come from a two-tuple map (fg,bg) with fallback `(entry_color, "#f5f5f5")`.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'return text' os_computer_use/logging.py && grep -c 'logger.log' os_computer_use/sandbox_agent.py` → expect return at :82 and 4 call sites wrapping Messages/logs.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "Logger log write_log_file print_colored css_color_map", limit: 6, fields: ["signature", "name", "file"] });
// expect Logger.log / write_log_file / print_colored / css_color_map
```

## Verdict
Adopt return-the-input logging wherever transcript fidelity must equal model-visible history; adapt to incremental appends for large sessions; omit the HTML rewrite when a plain text journal suffices.
