<!-- capsule-v2 -->
# State-gate lifecycle decorator — How do you make start/stop/set_channel idempotent and safe against wrong-state calls?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What does the check_if_running decorator actually retry, swallow, and raise?

## Retrying state assertion with self-recognition escape
**Path/Symbol:** `camel/societies/workforce/utils.py:check_if_running` (:734-839); applied at worker.py :93/:150/:207/:212 and workforce.py :5821/:5836, base.py :38.
**Signature:** `check_if_running(running: bool, max_retries=3, retry_delay=1.0, handle_exceptions=False)` decorating methods whose `self` carries `_running: bool`.
**Data Shape:** Raises `RuntimeError("The workforce is {not running|running}. Cannot perform {func}.")` when `_running != running` after retries; returns None on exhausted retries only when `handle_exceptions=True`.

### Decisive source
```python
except Exception as e:
    ...
    if isinstance(e, RuntimeError) and "workforce is" in str(e):
        raise                       # never retry a wrong-state error
    if retries < max_retries:
        time.sleep(retry_delay); retries += 1
```

**Flow:** wrapper loop `while retries <= max_retries` → assert `self._running == running`, on mismatch warn + sleep + retry (tolerates transient states during startup/teardown races), finally raise RuntimeError → run the method → any OTHER exception also retries up to max, then either logs-and-returns-None (handle_exceptions) or re-raises. The subtle bit: a RuntimeError whose message contains "workforce is" is re-raised IMMEDIATELY — the decorator must not retry its own state error. Note it uses blocking `time.sleep`, so decorated ASYNC methods (`async def start/stop/_listen_to_channel`) run this gate synchronously before their first await; that is acceptable precisely because the gate wraps only lifecycle entry points.
**Invariant:** `running=True` guards stop-paths (stop requires a running node), `running=False` guards start-paths — double-start and stop-of-dead-node fail loud (or log-and-None), never corrupt `_running`.
**Probe:** `grep -c '@check_if_running' camel/societies/workforce/*.py` → base.py:1, worker.py:4, workforce.py:6 (sum 11; utils.py holds only the definition).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "check_if_running decorator workforce running retries", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the state-gate decorator for lifecycle pairs, keeping the self-error no-retry rule. Adapt sleep to asyncio.sleep in async hosts. Omit handle_exceptions mode unless callers want soft lifecycle.
