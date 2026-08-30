<!-- capsule-v2 -->
# Coder preflight plane — what runs between the user's message and the LLM call, and why is the budget gate a consent gate?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How should an agent assemble its request (cache headers, token budget check, background cache warming) before the provider call without ever hard-blocking the user?

## format_messages → check_tokens → warm_cache, in that order
**Path/Symbol:** `aider/coders/base_coder.py`: call sites in `send_message` (:1429-1433); `Coder.format_messages` (:1333-1338), `Coder.warm_cache` (:1340-1394), `Coder.check_tokens` (:1396-1417), `Coder.move_back_cur_messages` (:1036-1046).
**Signature:** `format_messages(self) -> ChatChunks`; `check_tokens(self, messages) -> bool`; `warm_cache(self, chunks)`; `move_back_cur_messages(self, message)`.
**Data Shape:** ChatChunks → `.all_messages()` list of role dicts; warming state: `next_cache_warm: float`, `warming_pings_left: int`, `cache_warming_chunks`, daemon `threading.Timer`.

### Decisive source
```python
chunks = self.format_messages()          # + cache_control headers when add_cache_headers
messages = chunks.all_messages()
if not self.check_tokens(messages):
    return                                # user DECLINED to over-send; not an error
self.warm_cache(chunks)
```
```python
# check_tokens is consent, not enforcement:
if max_input_tokens and input_tokens >= max_input_tokens:
    ...advice (/drop, /clear, smaller files)...
    "It's probably safe to try and send the request, most providers won't charge..."
    if not self.io.confirm_ask("Try to proceed anyway?"):
        return False
return True
```

**Flow:** warm_cache arms only when `add_cache_headers AND num_cache_warming_pings AND ok_to_warm_cache`; keepalive delay 295 s (`AIDER_CACHE_KEEPALIVE_DELAY` override); the daemon worker sleeps 1 s ticks, sends `max_tokens=1` with the cached chunks every interval, reads `prompt_cache_hit_tokens`/`cache_read_input_tokens`, and warn-and-continues on any error. Cloned coders force `ok_to_warm_cache=False` (:188) so only the primary session warms. After the reply, `move_back_cur_messages(message)` promotes cur→done, crosses the summarize threshold (`summarize_start()`), appends the synthetic `user: message / assistant: "Ok."` pair, and empties cur.
**Invariant:** preflight may inform and ask but must not veto a confirmed send; cache-warming side effects must never run from derived/cloned coders.
**Probe:** deterministic anchors: DSH grep on base_coder.py — `warm_cache|check_tokens|format_messages` → 16 matches with the ordered call block at :1429-1433; clone-site `ok_to_warm_cache = False` at :188. Direct tests: **none upstream** for these methods outside chat-history fixtures — claims are source-pinned + anchor-verified (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "warm_cache", limit: 10 });
// rank-1: aider.aider.coders.base_coder.Coder.warm_cache aider/coders/base_coder.py 1340-1394 (check_tokens :1396-1417 rank-2)
```

## Verdict
Adopt the three-step preflight ordering and the consent-style budget gate with cost reassurance. Adapt the warming trigger (aider warms because prompt caches expire ~5 min) and env override name to your host. Omit the synthetic "Ok." pairing if your history surgery already preserves alternation another way (see reply-driving-pipeline.md).
