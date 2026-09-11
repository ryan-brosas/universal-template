<!-- capsule-v2 -->
# Hardened deserialization — hostile blobs are the threat model

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How is a resumed snapshot parsed safely when it may be untrusted and secret-bearing?

## Hardened deserialization
**Path/Symbol:** `src/agents/run_state.py` (from_string/from_json, `_validate_run_state_json_value` :2270-2286, redaction :2125-2168, trusted-message allowlist :5402-5490, nested-history digest :~3900).
**Signature:** `_validate_run_state_json_value(value: object) -> None`; `from_string` / `from_json`.
**Data Shape:** the snapshot may come from a database, queue, or user upload — untrusted, possibly secret-bearing.

### Decisive source
```python
def _validate_run_state_json_value(value: object) -> None:
    """Validate the exact built-in JSON tree without invoking caller-defined protocols."""
    if type(value) is dict:
        for key, item in dict.items(cast(dict[object, object], value)):
            if type(key) is not str:
                raise TypeError("Run state JSON contains an unsupported value")
            _validate_run_state_json_value(item)
        return
    if type(value) is list:
        for item in list.__iter__(cast(list[object], value)):
            _validate_run_state_json_value(item)
        return
    if type(value) in {str, int, float, bool, type(None)}:
        return
    raise TypeError("Run state JSON contains an unsupported value")
```

**Flow:** Exact-type tree validation first (:2270-2286) — only dict-with-str-keys/list/str/int/float/bool/None pass, using `type(...) is` checks that bypass subclass hooks. Redaction-by-default errors: any parse/validation failure overwrites the offending string with `<redacted>`, nulls locals, and detaches tracebacks — even catching BaseException while preserving CancelledError/KeyboardInterrupt/SystemExit (:2125-2168). Trusted-message allowlist (:5402-5490): only error messages matching a hardcoded list escape redaction, and only from UserError/ValueError carrying exactly one str arg; everything else surfaces redacted. Nested-history ownership refs get structural validation (non-negative indexes, len(digest)==64) THEN cryptographic verification: "Run state nested history ownership session digest does not match."
**Invariant:** Treat a resumed snapshot like a web request body — validate shape with exact-type checks first, fail closed on ambiguity, and let only an allowlist of known-safe error strings escape redaction.
**Probe:** :1702-1760 (unsafe-snapshot tests prove sensitive exception context is dropped); :8590-8599 (parametrizes malformed inputs against allowlisted messages); compatibility corpus `tests/fixtures/run_state/` replays real released snapshots.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_validate_run_state_json_value redacted trusted message", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-type-tree validation, redaction-by-default, trusted-message allowlist, and structural-then-crypto digest verification; adapt the allowlist contents; omit provider-specific message strings. Direct tests + compatibility corpus pin the behavior.
