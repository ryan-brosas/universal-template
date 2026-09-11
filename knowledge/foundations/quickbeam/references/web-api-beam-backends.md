<!-- capsule-v2 -->
# web-api-beam-backends — What BEAM primitives back localStorage, BroadcastChannel, and EventSource?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How are browser storage/messaging/streaming APIs implemented with zero extra infrastructure?

## ETS / :pg / stream:self seam
**Path/Symbol:** `lib/quickbeam/storage.ex` (:1-51); `lib/quickbeam/broadcast_channel.ex` (:1-26); `lib/quickbeam/event_source.ex:open/2 + stream_loop/4` (:5-61).
**Signature:** Storage: named public ETS `:quickbeam_local_storage`, handlers get/return plain terms, `key/1` sorts ALL keys then Enum.at (O(n) per access). BroadcastChannel: `:pg.join/@scope/name`; post fans out `{:broadcast_message, name, msg}` to members EXCEPT sender. EventSource: Task + `:httpc.request(:get, {url, headers}, [], [sync: false, {:stream, :self}])`.
**Data Shape:** All three are registered in runtime.ex @browser_handlers as `"__storage_*"`, `"__broadcast_*"`, `"__eventsource_*"` entries; broadcast trio uses `{:with_caller, fun}` because identity = caller pid.

### Decisive source
```elixir
# BroadcastChannel — the whole module:
def join([name], caller),    do: :pg.join(@scope, name, caller)
def post([name, message], caller) do
  for pid <- :pg.get_members(@scope, name), pid != caller do
    send(pid, {:broadcast_message, name, message})
  end
  :ok
end

# EventSource streaming receive loop (per chunk):
new_buffer = buffer <> to_string(chunk)
{events, remaining} = parse_sse_events(new_buffer)   # split on "\n\n", keep tail
for event <- events, do: send(parent, {:eventsource_event, id, event})
stream_loop(request_id, parent, id, remaining)
```

**Flow:** localStorage = node-global KV (no scoping per origin/runtime — deliberate simplification; clear() wipes globally). BroadcastChannel membership IS the runtime GenServer pid (`{:with_caller, ...}` passes it), so delivery is a raw send into the GenServer which forwards to JS via Native.send_message. SSE parser keeps the trailing partial block as buffer and joins multi-line `data:` with "\n"; comment lines (`:`) ignored.
**Invariant:** (1) `pid != caller` exclusion implements same-channel-no-echo semantics. (2) SSE 30 s receive timeout treats silence as error — real keep-alives need a longer budget. (3) Storage key() sorting gives deterministic ordering but is O(n log n) each call — porters scaling this need an ordered structure. (4) All three rely on lazy singleton init (`init/0` or ensure_* guards) because handler Tasks may run before application start completes.
**Probe:** `grep -c ':pg.get_members' lib/quickbeam/broadcast_channel.ex` → 1.
**Probe:** `grep -c 'read_concurrency' lib/quickbeam/storage.ex lib/quickbeam/fetch.ex` → 1 and 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "broadcast pg join members eventsource stream", limit: 10 });
```

## Verdict
Adopt these as reference minimal backends (ETS-KV, pg-groups fan-out, httpc-stream SSE) when you need browser-shaped APIs without external deps; adapt scoping/persistence to your security model; omit SSE if your fetch layer already streams. Coverage: all three paths no_recorded_issue+metadata_match.
