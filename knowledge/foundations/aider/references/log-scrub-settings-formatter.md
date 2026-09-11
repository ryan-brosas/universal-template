<!-- capsule-v2 -->
# Log-scrub settings formatter — last-4 mask applied to every rendered value

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When a CLI dumps its full effective configuration for `--verbose` debugging and echoes the launching command line into the log, how do you keep API keys out of both?

## One scrubber, three surfaces: raw command line, parser.format_values(), and the sorted vars(args) dump
**Path/Symbol:** `aider/format_settings.py`: `scrub_sensitive_info(args, text)` (:1-9), `format_settings(parser, args)` (:12-26); consumers: `main.py` :746 (verbose settings dump) and :750 (`cmd_line = scrub_sensitive_info(args, " ".join(sys.argv))` logged via `io.tool_output(..., log_only=True)`; import at :29).
**Signature:** scrub replaces each known secret with `"..." + last_4_chars` — keys currently covered: `args.openai_api_key`, `args.anthropic_api_key`.
**Data Shape:** format_settings appends an "Option settings:" block listing EVERY argparse dest with truthy-or-None value after per-value scrubbing.

### Decisive source
```python
def scrub_sensitive_info(args, text):
    if text and args.openai_api_key:
        last_4 = args.openai_api_key[-4:]
        text = text.replace(args.openai_api_key, f"...{last_4}")
    if text and args.anthropic_api_key:
        last_4 = args.anthropic_api_key[-4:]
        text = text.replace(args.anthropic_api_key, f"...{last_4}")
    return text
...
for arg, val in sorted(vars(args).items()):
    if val:
        val = scrub_sensitive_info(args, str(val))
    show += f"  - {arg}: {val}\n"
```

**Flow:** verbose mode → format_settings renders parser defaults + runtime overrides, scrubbing each value; separately the literal invocation line is scrubbed before it reaches the chat-log file. Heading normalization inserts newlines before "Environment Variables:" / "Defaults:" for readability.
**Invariant:** masking keeps the last 4 chars so users can verify WHICH key is in play — the invariant is "recognizable but not usable"; scrubbing is substring-replacement so keys embedded mid-string (e.g. inside URLs on the command line) are still caught.
**Probe:** deterministic anchors: `grep -nF 'scrub_sensitive_info' aider/main.py | head -2` → :29 import + :750 call-site. Direct tests: none upstream for format_settings.py itself (source-pinned caveat); test_utils.py covers sibling formatting helpers.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "scrub_sensitive_info", limit: 3 });
// rank-1: aider.aider.format_settings.scrub_sensitive_info aider/format_settings.py 1-9
```

## Verdict
Adopt verbatim as the minimal viable secret-hygiene layer for CLI agents; extend the key list to every credential your harness accepts. Omit nothing — logging the UNSCRUBBED argv is the classic leak this capsule exists to prevent.
