<!-- capsule-v2 -->
# Session hot-standby transfer — moving the in-memory session cache between deploys over Unix sockets

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9` (`lib/plausible/session/transfer.ex` + `transfer/{tinysock,alive}.ex`); Codebase Memory `ext-analytics`. **Question:** How do rolling deploys avoid resetting every visitor's session when the in-memory session cache dies with the old node?

## Replica/primary takeover protocol
**Path/Symbol:** `lib/plausible/session/transfer.ex:init_takeover` (:127-137), `handle_replica` (:104-123), `session_version/0` (:172-180).
**Signature:** one-time `Task` replica scans socket dir sorted by ctime ASC (oldest primary first) and calls each; primary's TinySock handler answers `{@cmd_list_cache_names, version}` / `{@cmd_dump_cache, cache}` / `:done`.
**Data Shape:** commands are atoms; cache dump = `[{{site_id, user_id}, %ClickhouseSessionV2{}}]` straight from ConCache ETS via `Cache.Adapter.cache2list/1`.

### Decisive source
```elixir
defp session_version do
  [ClickhouseSessionV2.module_info(:md5),
   Cache.Adapter.module_info(:md5),
   Session.CacheStore.module_info(:md5),
   Session.Transfer.module_info(:md5)]
end
# guard: if session_version == session_version() and attempted?(parent) -> names else []
```

**Flow:** new node boots → replica Task lists `tinysock*` files → for each old primary: fetch cache names → parallel `Task.async` dump per partition → re-put into local cache → send `:done` → old node's counter unblocks its `Alive` process.
**Invariant:** (1) The 4-module MD5 tuple is a wire-format fingerprint — a struct change without a matching code deploy would silently deserialize garbage, so mismatched versions answer `[]` and sessions reset instead of corrupting; (2) dumps read ETS directly (no TTL bookkeeping) which is safe ONLY because records are re-put through `Adapter.put` preserving original timestamps.
**Probe:** `test/plausible/session/transfer_test.exs:7` ("it works") spins TWO peer nodes, pushes 250 events, starts a third node and asserts `all_sessions_sorted(new) == all_sessions_sorted(old)`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "session/transfer", limit: 10 });
```

## TinySock framing + graceful-shutdown latch
**Path/Symbol:** `lib/plausible/session/transfer/tinysock.ex:sock_send` (:137-139), `sock_recv` (:141-150), `sock_connect_or_rm` (:120-134); `alive.ex:loop/1`.
**Signature:** frame = `"tinysock" <> <<size::64-little>> ++ term_to_iovec(msg)`; reply is `binary_to_term(payload, [:safe])`; >64MB replies chunk-read at 5MB to dodge `:enomem`.
**Data Shape:** Unix domain sockets named `tinysock<url_encode64(rand4)>`; 10 acceptors pre-spawned; failed connect (non-timeout) deletes the stale socket FILE.
**Flow:** `Alive` traps exits and on terminate polls `until.()` every 500ms — here "did at least one replica take over?" (`counters.get(given_counter) > 0`) — holding shutdown up to its 15s `shutdown:` value.
**Invariant:** The `[:safe]` binary_to_term flag is a hard security boundary: the socket is a filesystem path any local process could write. A porter switching to `binary_to_term/1` turns deploys into RCE.
**Probe:** `grep -c 'binary_to_term' lib/plausible/session/transfer/tinysock.ex` → 1 (:145); `grep -n '@five_mb' ...tinysock.ex` → :152.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^call$", fields: ["lines"], limit: 6 });
```

## Verdict
Adopt version-fingerprinted cache handoff with safe-term framing; adapt socket path/dir conventions; omit if your deployment keeps caches external.
