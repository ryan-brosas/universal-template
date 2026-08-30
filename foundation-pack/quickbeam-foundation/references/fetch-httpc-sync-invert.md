<!-- capsule-v2 -->
# fetch-httpc-sync-invert — How do you expose an async-looking fetch when the host call is synchronous?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How is fetch() implemented over :httpc with cancellation and hard timeouts?

## httpc sync:false inversion seam
**Path/Symbol:** `lib/quickbeam/fetch.ex:fetch/1` (:17-78), `cancel/1` (:81-88), `ssl_opts/1` (:119-128).
**Signature:** handler receives `[%{"url" => ..., "method" => ..., "headers" => [[k,v]], "body" => ..., "fetchId" => ...}]` and returns a plain map (the resolved Response shape); errors are RAISES (translated to JS rejections by the dispatch layer).
**Data Shape:** `:httpc.request(method, req, http_opts, [sync: false, body_format: :binary], :quickbeam)` returns `{ok, request_id}`; completion arrives as `{:http, {request_id, {{_,status,reason}, headers, body}}}` or `{:http, {request_id, {:error, reason}}}`.

### Decisive source
```elixir
{:ok, request_id} = :httpc.request(atomize_method(method), request,
    [ssl: ssl_opts(uri.host), autoredirect: redirect == "follow",
     relaxed: true, timeout: 30_000, connect_timeout: 10_000],
    [sync: false, body_format: :binary], :quickbeam)
:ets.insert(@table, {fetch_id, request_id})
result = receive do
  {:http, {^request_id, {{_, status, reason}, resp_headers, resp_body}}} ->
    %{"status" => status, "headers" => [...], "body" => {:bytes, IO.iodata_to_binary(resp_body)}, ...}
  {:http, {^request_id, {:error, reason}}} -> raise "fetch failed: #{inspect(reason)}"
after
  30_000 -> cancel_httpc(request_id); raise "fetch timed out"
end
:ets.delete(@table, fetch_id)
```

**Flow:** dedicated `:quickbeam` httpc profile started lazily → async request → ETS registry maps fetchId→request_id (enables AbortController-style cancel via `:ets.take` + cancel_request) → BLOCKING receive with 30 s cap → on timeout cancel then raise → registry row deleted on both paths.
**Invariant:** (1) TLS is verify_peer + cacerts_get + SNI + https hostname match — never downgrade; porters copying "simple" httpc snippets ship insecure fetch. (2) Method allowlist (@known_methods) rejects arbitrary verbs with ArgumentError. (3) Body handling: GET/HEAD/OPTIONS/DELETE or nil body ⇒ 2-tuple request; else content-type sniffed from headers defaulting application/octet-stream. (4) The ETS table is named/public/read_concurrency and lazily created (`ensure_table`) because handlers run in Task processes, not the runtime GenServer.
**Probe:** `grep -c 'ets.take' lib/quickbeam/fetch.ex` → 1.
**Probe:** `grep -c 'verify_peer' lib/quickbeam/fetch.ex` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "httpc fetch request ets cancel", limit: 10 });
```

## Verdict
Adopt sync:false-inverted-to-receive as the minimal fetch backend plus the ETS cancel registry; adapt transport to your HTTP client; keep strict TLS defaults and method allowlisting. Coverage: fetch.ex no_recorded_issue+metadata_match; direct tests under test/web_apis exercise fetch at the pin.
