<!-- capsule-v2 -->

# Logs subscriber selection & auth ladder — How do you pick the right stream client from config and fail fast on bad credentials?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect` (graph not connected this pass — direct source/test reads; see work record). **Question:** What is the correct config→client decision ladder for a CONSUMER (vs a fire-and-forget producer), and how should websocket auth denial be surfaced?

## Cloud-prefix / any-URL / ephemeral-start / raise ladder, with soft and hard auth denial both mapped to one actionable error

**Path/Symbol:** `src/prefect/logging/clients.py:get_logs_subscriber (97-137)`, `_get_api_url_and_key (83-94)`, `PrefectLogsSubscriber.__aenter__ (219-227)`, `_reconnect` auth block (243-264), `PrefectCloudLogsSubscriber (348-378)`.

**Signature:** `get_logs_subscriber(filter=None, reconnection_attempts=10, reconnect_on_clean_close=False) -> PrefectLogsSubscriber`.

**Data Shape:** decision inputs are live settings (`PREFECT_API_URL`, `PREFECT_CLOUD_API_URL`, `PREFECT_SERVER_ALLOW_EPHEMERAL_MODE`); the Cloud twin additionally requires an explicit `api_key` (resolved against `PREFECT_API_KEY`, `ValueError` if either missing). Auth token sent = `_api_key or _auth_token` where `_auth_token` is `PREFECT_API_AUTH_STRING`.

### Decisive source
```python
# get_logs_subscriber — note the LAST arm raises; there is no null fallback:
if isinstance(api_url, str) and api_url.startswith(PREFECT_CLOUD_API_URL.value()):
    return PrefectCloudLogsSubscriber(...)
elif api_url:
    return PrefectLogsSubscriber(api_url=api_url, ...)
elif PREFECT_SERVER_ALLOW_EPHEMERAL_MODE:
    server = SubprocessASGIServer(); server.start()
    return PrefectLogsSubscriber(api_url=server.api_url, ...)
else:
    raise ValueError("No Prefect API URL provided. ...")

# _reconnect — BOTH denial shapes map to one friendly error carrying the reason:
auth_token = self._api_key or self._auth_token
await self._websocket.send(orjson.dumps({"type": "auth", "token": auth_token}).decode())
try:
    message = orjson.loads(await self._websocket.recv())
    assert message["type"] == "auth_success", message.get("reason", "")
except AssertionError as e:
    raise Exception("Unable to authenticate to the log stream. ... Reason: {e.args[0]}")
except ConnectionClosedError as e:      # server closed before replying (WS_1008)
    reason = getattr(e.rcvd, "reason", None)
    raise Exception("Unable to authenticate to the log stream. ... Reason: {reason}") from e
```

**Flow:** config decides the class (cloud prefix → Cloud twin; any URL → self-hosted; no URL + ephemeral allowed → start a local subprocess server and point at it; otherwise raise). The initial connect in `__aenter__` deliberately has NO retry/error handling — first-connect failures are "most likely a permission or configuration issue that should propagate" (comment :221-222). Auth is a subprotocol handshake: send token, expect `auth_success`; a soft denial (explicit `auth_failure` message) and a hard denial (server closes the socket before replying) both become the same actionable `Exception` embedding the server's reason. Falsy tokens are legal: `None` and `""` are sent as-is because self-hosted servers accept unauthenticated streams. The Cloud twin's only delta is credential precedence — an explicit `api_key` wins over the environment auth string.

**Invariant:** (1) A consumer must NOT have a null/no-op fallback arm: silently dropping every log hides misconfiguration, whereas a fire-and-forget producer may degrade to null (contrast P1's `EventsWorker.instance()` NullEventsClient arm). (2) Both denial shapes must be caught — catching only the explicit failure message misses servers that close the socket instead of replying. (3) First-connect errors propagate raw; only post-connect disconnects enter the retry ladder. (4) Falsy-but-present tokens must not be treated as "no token" — `or`-chaining on the token value would break unauthenticated self-hosted use.

**Probe:** direct tests `tests/logging/test_logs_subscriber.py`: `:91-113` (ladder arms: server/ephemeral/cloud construction + `ValueError` when URL missing and ephemeral disabled); `:354-381 test_subscriber_raises_on_invalid_auth_with_soft_denial` and `:384-412 test_cloud_subscriber_raises_on_invalid_auth_with_hard_denial` (both match "Unable to authenticate", zero logs delivered); `:645-683 test_subscriber_auth_with_none_token` and `:686-723 test_subscriber_auth_with_empty_token` (falsy tokens sent verbatim, `auth_success` accepted); `:515-528 test_get_api_url_and_key_missing_values` (any-missing → ValueError).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^get_logs_subscriber$", "limit": 3}'
```
(expected rank-1: `get_logs_subscriber Function src/prefect/logging/clients.py 97-137`; graph was NOT connected in the mining session that authored this capsule — verify live before relying on line numbers.)

## Verdict
Adopt the four-arm ladder with a RAISE last arm for consumers, dual-shape auth-denial mapping that preserves the server reason, and propagate-raw first connect. Adapt the settings names and ephemeral-server start to your host; omit Prefect's Subprotocol("prefect") framing and the Prometheus connection counters.
