<!-- capsule-v2 -->
# Provider timeout ladder — What does an "unset" outbound LLM timeout mean, and how do streaming and unary calls differ?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How should a gateway parse timeout env vars so that unset means unlimited, garbage means a safe default, and streaming gets an idle cap instead of a total cap?

## Timeout env parsing seam
**Path/Symbol:** `backend/open_webui/env.py` (574-591 main+idle, 610-617 model-list, 640-648 tool-server); consumed by `backend/open_webui/utils/session_pool.py:42-50`.
**Signature:** module-level ints/None; `def get_client_timeout(stream: bool = False) -> aiohttp.ClientTimeout`.
**Data Shape:** `AIOHTTP_CLIENT_TIMEOUT`: int|None; `AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT`: int|None; `AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST`: int; prebuilt `_CLIENT_TIMEOUT = ClientTimeout(total=…)`, `_CLIENT_STREAM_TIMEOUT = ClientTimeout(total=…, sock_read=idle)`.

### Decisive source
```python
_aiohttp_timeout_raw = os.getenv('AIOHTTP_CLIENT_TIMEOUT', '')
try:
    AIOHTTP_CLIENT_TIMEOUT = int(_aiohttp_timeout_raw) if _aiohttp_timeout_raw else None
except (ValueError, TypeError):
    AIOHTTP_CLIENT_TIMEOUT = 300

# Optional between-chunks idle cap for streaming aiohttp requests.
AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT = os.getenv('AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT', '')
if AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT == '':
    AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT = None
else:
    try:
        AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT = int(AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT)
    except (ValueError, TypeError):
        AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT = None

if AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT is not None and AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT <= 0:
    AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT = None
```

```python
_model_list_timeout_raw = os.getenv(
    'AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST',
    os.getenv('AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST', '10'),
)
```

**Flow:** parse at import → unset ('') means NO total cap (`total=None`), unparseable means fallback 300 (model-list: 10) → streaming calls reuse the SAME total but add `sock_read` idle detection only when the idle env is set and > 0 → per-request selection is just `get_client_timeout(stream=is_streaming_request)`.
**Invariant:** three distinct failure semantics must not collapse: unset→unlimited, garbage→default, ≤0-idle→disabled. Streaming never shortens or lengthens the total — only adds between-chunks liveness. Short-census calls (model lists) get their own tight budget with legacy env-name compatibility.
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "AIOHTTP_CLIENT_TIMEOUT = int(_aiohttp_timeout_raw) if _aiohttp_timeout_raw else None" backend/open_webui/env.py` → line 576; `grep -n "AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST" backend/open_webui/env.py` → line 612.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_client_timeout stream sock_read ClientTimeout", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves `utils.session_pool.get_client_timeout` 49-50 and `env.AIOHTTP_CLIENT_*` variables.

## Verdict
Adopt: the three-way unset/garbage/clamped semantics and stream=idle-cap-not-total-cap design. Adapt: default values (300s / 10s / idle-off) to host SLOs. Omit: tool-server/MCP-specific sibling timeouts unless porting those planes. Caveat: `AIOHTTP_CLIENT_TIMEOUT=''` deliberately disables the total cap — do not "fix" it to a default when porting; zero direct tests upstream.
