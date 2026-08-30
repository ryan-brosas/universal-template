<!-- capsule-v2 -->
# Ping/identify handshake — how do you know the process behind a stale endpoint file is YOUR daemon?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** After a crash leaves a `.port`/`.sock` file behind (and the port got reused), how does a client avoid mistaking an unrelated listener for its daemon — and avoid signalling a recycled PID?

## pong-shape liveness + bool-rejecting PID validation
**Path/Symbol:** `src/browser_harness/_ipc.py:ping` (:109-127) and `identify` (:130-162); server side `daemon.py:handle` ping branch (:556).
**Signature:** `ping(name, timeout=1.0) -> bool`; `identify(name, timeout=1.0) -> int|None`.
**Data Shape:** request `{"meta":"ping"}`; response `{"pong": true, "pid": <int>, "browser_kind": "cloud|cdp|local"}`. Any other JSON value (list/scalar/hostile dict) = not our daemon.

### Decisive source
```python
resp = request(c, token, {"meta": "ping"})
# Anything that isn't a {pong: True} dict counts as "not our daemon"
return isinstance(resp, dict) and resp.get("pong") is True

pid = resp.get("pid")
# type(pid) is int (not isinstance) intentionally rejects bool:
# isinstance(True, int) is True in Python — {"pid": true} would become PID 1!
# Also reject 0/negatives: os.kill(0) signals the whole process group,
# os.kill(-1) everything the caller can. Upper bound 2**31 (pid_t).
return pid if type(pid) is int and 0 < pid < (1 << 31) else None
```

**Flow:** bare connect proves *a* listener exists → ping proves it answers *our* protocol → identify extracts a validated PID usable for signals.
**Invariant:** never `.get()` blindly on an unvalidated response; never trust a PID file on disk when the live daemon self-reports. A successful TCP connect is NOT identity.
**Probe:** `tests/unit/test_ipc.py:44` `test_identify_rejects_boolean_pid`, `:53` `test_identify_rejects_boolean_false_pid`, `:80` `test_identify_returns_none_when_pong_is_not_true`, `:86` `test_identify_rejects_zero_and_negative_pids`, `:111` `test_ping_handles_non_dict_payload`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "identify rejects boolean pid pong", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt wholesale — this is the portable core of any "daemon + endpoint file" design (the bool-rejection trap alone justifies the capsule). Adapt the response fields; omit `browser_kind` unless you need self-reported mode. Probes are directly test-pinned.
