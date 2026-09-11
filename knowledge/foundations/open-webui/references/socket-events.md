<!-- capsule-v2 -->
# Socket event emitter/caller pair — how do chat events reach every device of a user across instances, and how does the backend safely call back into one browser session?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** Where may an emit be dropped instead of sent, which events persist to the chat row, and what makes an sio.call target safe?

## Room-gated emit + session-owned call
**Path/Symbol:** `backend/open_webui/socket/main.py:get_event_emitter` (lines 968-1097), `get_event_call` (1100-1133), alias `get_event_caller = get_event_call` (1136); wiring in `backend/open_webui/utils/middleware.py:get_event_emitter_and_caller` (2990-3005).
**Signature:** `async def get_event_emitter(request_info, update_db=True)` · `async def get_event_call(request_info)` · `async def get_event_emitter_and_caller(metadata) -> tuple[emitter|None, caller|None]`.
**Data Shape:** `request_info`: `{user_id, chat_id, message_id, session_id?, internal?}`; wire payload `{'chat_id', 'message_id', data, ('internal': True)}` on event `'events'`; broadcast room `f'user:{user_id}'`; `SESSION_POOL` maps client session_id -> dict whose `'id'` is the owning user_id.

### Decisive source
```python
room = f'user:{user_id}'
# Local rooms are authoritative; Redis may have listeners on another instance.
if WEBSOCKET_MANAGER == 'redis' or room in sio.manager.rooms.get('/', {}):
    await sio.emit('events', {...}, room=room)

if save_to_chat:   # update_db and message_id and is_saved_chat_id(chat_id)
    event_type = event_data.get('type')   # status | message | replace |
                                          # embeds | files | source/citation
```

and the caller side (session_id is client-supplied):
```python
session = SESSION_POOL.get(session_id)
if session is None or session.get('id') != request_info.get('user_id'):
    return {'error': 'Client session disconnected.'}
...
except TimeoutError:
    if SESSION_POOL.get(session_id) == session:   # identity-checked eviction
        try: del SESSION_POOL[session_id]
        except KeyError: pass
```
**Flow:** factory returns `None` unless required keys exist (emitter: `user_id+chat_id+message_id`; caller: those plus `session_id`) → `channel:`-prefixed chat_ids route to a separate channel emitter → each emit checks the room gate, then persists per type (`message` appends content; `replace` overwrites; `embeds`/`files`/`sources` merge with `touch=False`) → middleware builds both handles from metadata; the caller exists only for direct tools / code interpreter.
**Invariant:** outside redis mode an event is emitted only when the room exists locally (never blind-fanned into a void); persistence applies only to saved chats carrying a `message_id`, and non-content upserts never bump the chat `touch`; a caller RPC targets only a live session owned by the requesting user, and timeout evicts that exact session object only.
**Probe:** no test runner at this HEAD (zero test files repo-wide) — deterministic anchors executed: `grep -n "Local rooms are authoritative" backend/open_webui/socket/main.py` hits line 984; `grep -n "get_event_caller = get_event_call" backend/open_webui/socket/main.py` hits line 1136.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_event_emitter get_event_call session pool redis room fanout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the room-presence emit gate, per-type persistence algebra with touch control, and ownership-checked + identity-evicting session RPC; adapt the socket.io manager introspection (`sio.manager.rooms`) and SQLAlchemy upserts to your transport/store; omit the channel-emitter branch and the Svelte client protocol. Coverage caveat: none recorded for these paths; direct tests absent at this pin.
