<!-- capsule-v2 -->
# Cloud agent-event envelope — how do you type local agent telemetry events so a server can safely fill in identity fields later?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you model "replayable task event" payloads produced by a client that does NOT know its own authorization identity, without leaking oversized content or blocking construction on partial agents?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/cloud_events.py` whole (284L) — `UpdateAgentTaskEvent.from_agent` (:35-59), `CreateAgentOutputFileEvent.validate_file_size` (:73-86), `CreateAgentStepEvent.from_agent_step` (:146-184), `CreateAgentTaskEvent.from_agent` (:206-227), `CreateAgentSessionEvent.from_agent` (:244-272). Callers: `Agent.run` / `Agent.run_sync`, beta twin `_dispatch_run_start_events`.
**Signature:** `from_agent(cls, agent) -> Self` classmethods on every event; `field_validator`s on the two free-size string fields (`file_content`, `screenshot_url`).
**Data Shape:** five `BaseEvent` subclasses (bubus). Budgets: `MAX_STRING_LENGTH = 500000`, `MAX_URL_LENGTH = 100000`, `MAX_TASK_LENGTH = 100000`, `MAX_COMMENT_LENGTH = 2000`, `MAX_FILE_CONTENT_SIZE = 50MB` (note: the constant's inline comment says "100K chars" but the value is 500k — trust the value). IDs are `uuid7str` defaults.

### Decisive source
```python
# Every from_agent: identity is a SERVER-FILLED placeholder, never guessed client-side
user_id='',  # To be filled by cloud handler
device_id=agent.cloud_sync.auth_client.device_id
if hasattr(agent, 'cloud_sync') and agent.cloud_sync and agent.cloud_sync.auth_client
else None,          # hasattr-guarded duck typing: partial agents still construct
...
browser_session_live_url='',   # To be filled by cloud handler
browser_session_cdp_url='',    # To be filled by cloud handler
'cookies': [], 'secrets': {},  # TODO: send secrets safely so tasks can be replayed
```
```python
# CreateAgentOutputFileEvent.validate_file_size — REASSIGNS v: prefix is stripped
if ',' in v:
    v = v.split(',')[1]              # stored value loses the data: URL prefix
estimated_size = len(v) * 3 / 4      # decoded-size estimate, ~33% inflation rule
if estimated_size > MAX_FILE_CONTENT_SIZE:
    raise ValueError(...)

# CreateAgentStepEvent.validate_screenshot_size — separate variable: keeps data: URL
base64_part = v.split(',')[1]        # v itself is returned unchanged
estimated_size = len(base64_part) * 3 / 4
```
**Flow:** agent lifecycle point → `from_agent` duck-types whatever attributes exist (`_task_start_time` gate raises ValueError; everything else degrades to `False`/`None`/`{}`) → per-field pydantic budgets clamp strings at construction → size validators estimate decoded bytes as `len(base64)*3/4` after stripping any data-URL prefix → event goes onto the bus; transport half lives in `sync/service.py` (see sync-cloud-event-tunnel).
**Invariant:** `user_id=''` and session live/cdp URLs are always placeholders for a server to overwrite — the client NEVER fabricates them; file_content normalizes to bare base64 while screenshot_url stays a full `data:` URL (asymmetry is intentional-looking and probe-pinned); base64 rejection boundary is `len > 4/3 × MAX` (50 MB of 'A' passes because its estimate is only 39.3 MB); `UpdateAgentTaskEvent.from_agent` hard-fails without `_task_start_time` while all other agent attributes soft-degrade.
**Probe:** no dedicated upstream unit test exists (grep of tests/ for cloud_events → empty); documented caveat. Executed in-process probe (repo .venv, cwd=repo root): data-URL file_content stored prefix-stripped (`QUJD…`); `len == MAX_FILE_CONTENT_SIZE` accepted, `2×MAX` rejected with ValidationError ("Value error"); `UpdateAgentTaskEvent.from_agent(Bare())` → ValueError "Agent must have _task_start_time attribute".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "CreateAgentOutputFileEvent CreateAgentStepEvent CreateAgentTaskEvent UpdateAgentSessionEvent from_agent cloud handler", limit: 10, fields: ["signature"] });
```
Top hits: all five `from_agent*` methods + both validators at exactly the cited lines (:35-59, :75-86, :134-144, :147-184, :207-227, :245-272).

## Verdict
Adopt the placeholder-identity envelope pattern (client leaves auth fields empty with an explicit contract comment; server fills), the hasattr-guarded duck-typed factory so events construct from partial agents, and per-field byte budgets enforced by pydantic validators with the `len*3/4` base64 estimator. Adapt budget values to your transport, and pick ONE normalization convention for data-URLs (this repo deliberately differs between file and screenshot fields). Omit the GIF-specific default content_type and the commented-out secrets replay until you have a safe-replay design.
