<!-- capsule-v2 -->
# WriteBuffer — byte-counted RowBinary batching with compile-time-frozen schema

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How are events/sessions batched into ClickHouse inserts, and why is the INSERT statement precomputed at compile time?

## One generic GenServer, many typed buffers
**Path/Symbol:** `lib/plausible/ingestion/write_buffer.ex:handle_cast({:insert, row_binary})` (:44-60), `compile_time_prepare` (:118-156); typed shells `lib/plausible/session/write_buffer.ex:insert` (:25-38).
**Signature:** `insert(server, row_binary) :: :ok` via `GenServer.cast` (fire-and-forget, backpressure-free); flush via `GenServer.call(..., :infinity)`.
**Data Shape:** buffer is an iodata list + byte counter (`buffer_size`); thresholds from app env `max_buffer_size` / `flush_interval_ms`.

### Decisive source
```elixir
if state.buffer_size >= state.max_buffer_size do
  Logger.notice("#{state.name} buffer full, flushing to ClickHouse")
  Process.cancel_timer(state.timer)
  do_flush(state)
  new_timer = Process.send_after(self(), :tick, state.flush_interval_ms)
  {:noreply, %{state | buffer: [], timer: new_timer, buffer_size: 0}}
end
```

**Flow:** producers encode rows to `Ch.RowBinary` bytes themselves → cast bytes into buffer → flush on size OR interval tick OR explicit call OR `terminate/2`. `do_flush` issues ONE `IngestRepo.query!(insert_sql, [header | buffer], insert_opts)` with `encode: false` — the header is a pre-encoded "names and types" binary prefix, rows follow raw.
**Invariant:** (1) Buffering BYTES not structs makes size accounting O(1) (`IO.iodata_length`) and removes per-row encoding from the GenServer; (2) SQL string, field list, and header are computed ONCE at module compile (`unquote(header)` in child_spec) — per-insert work is just concatenation; (3) `trap_exit` + EXIT-swallowing `handle_info` (:69-72) keep the buffer alive when linked processes die; `terminate` does a best-effort final flush (data since last flush can still be lost on hard crash — durability delegated to ClickHouse's own WAL/fsync).
**Probe:** `test/plausible/ingestion/write_buffer_test.exs:10` ("keeps running and logs the reason when a linked process exits") pins the EXIT-swallow behavior.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^compile_time_prepare$|^handle_cast$", fields: ["lines"], limit: 6 });
```

## Typed shell does BoolUInt8 dump before encode
**Path/Symbol:** `lib/plausible/session/write_buffer.ex` (:25-38).
**Flow:** each session's `is_bounce` boolean is dumped through the custom `BoolUInt8` Ecto type, then fields fetched in EXACTLY `fields` order and encoded as one row-binary blob.
**Invariant:** Column order comes from `schema.__schema__(:fields)` minus `[:acquisition_channel, :interactive?]` (computed columns) — reordering either side corrupts every row silently. The `Map.fetch!` (not `.field`) ensures a missing key crashes loudly instead of writing nil.
**Probe:** `grep -n 'fields_to_ignore' lib/plausible/ingestion/write_buffer.ex` → :121 use + :158 def (= `[:acquisition_channel, :interactive?]`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "session/write_buffer.ex", fields: ["lines"], limit: 8 });
```

## Verdict
Adopt byte-buffered cast-based batching with compile-time frozen INSERT; adapt thresholds; omit the relay/remote persistor twins if single-node.
