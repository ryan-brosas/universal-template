<!-- capsule-v2 -->
# Opt-out telemetry with a detached sender — how do you collect usage without ever blocking the CLI or leaking secrets?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Telemetry must be best-effort, opt-out, and never slow or leak — what invariants make that safe?

## env+config opt-out, property allowlist, detached subprocess sender
**Path/Symbol:** `src/browser_harness/telemetry.py:is_enabled` (:102-105), `_safe_properties` (:128-144), `_send_detached` (:189-206), `_detect_agent_client` (:164-170), `capture_cli_event` (:247-294).
**Signature:** `capture(event, properties=None)`; `capture_cli_event(*, action, command, ...)`.
**Data Shape:** disable envs `BH_TELEMETRY`/`BROWSER_HARNESS_TELEMETRY`/`ANONYMIZED_TELEMETRY` = "0"/"false"/... ; config `telemetry.json` `disabled` flag; `FORBIDDEN_KEYS` list; install_id uuid.

### Decisive source
```python
def _safe_properties(properties):
    for key, value in (properties or {}).items():
        safe_key = re.sub(r"[^A-Za-z0-9_$.-]+", "_", str(key))[:80]
        lowered = safe_key.lower()
        if not safe_key or any(word in lowered for word in FORBIDDEN_KEYS):
            continue                                   # drop secrets by KEY NAME
        if isinstance(value, bool) or value is None: out[safe_key] = value
        elif isinstance(value, int | float): out[safe_key] = value
        else:
            safe_value = str(value)
            if "://" in safe_value: safe_value = "[redacted]"   # URLs → redacted
            out[safe_key] = safe_value[:120]

def _send_detached(payload):
    process = subprocess.Popen([sys.executable, "-c", _DETACHED_SENDER_SOURCE],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)                        # detached: CLI never blocks
    process.stdin.write(json.dumps(job).encode()); process.stdin.close()
```

**Flow:** `is_enabled` → env-disabled OR config-disabled ⇒ skip → build payload with `_safe_properties` (drop by forbidden key-name, redact URLs, cap length) → hand to a detached `python -c` subprocess over stdin → return immediately. Agent client detected from env markers (`HERMES_SESSION_ID`→hermes, `CLAUDECODE`, `CODEX_SANDBOX`, ...).
**Invariant:** telemetry is structurally incapable of blocking (detached sender) or leaking (key-name allowlist + URL redaction + 120-char cap); opt-out honored by BOTH env and persisted config.
**Probe:** no direct unit test (network + subprocess) — coverage caveat: `_safe_properties` behavior verified by reading; `tests/unit/test_run.py` covers the CLI-event wiring indirectly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "telemetry detached sender safe_properties forbidden", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the detached-sender + key-name-allowlist + URL-redaction model for any telemetry; adapt disable envs and agent markers; omit nothing. Coverage caveat noted.
