<!-- capsule-v2 -->
# nio4r event loop — how do you run a forked per-process line server with mid-connection STARTTLS and drain-based shutdown?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How does one selector drive accept, read, TLS handshake completion, and graceful process exit — including swapping a plain socket for TLS without dropping buffered state?

## SMTPServer::Server#run_event_loop
**Path/Symbol:** `app/lib/smtp_server/server.rb:SMTPServer::Server#run_event_loop` (:97–296), `ssl_context` (:60–70), `unlisten` (:91–95).
**Signature:** `run_event_loop → never returns` (exits via `Process.exit(0)` when the selector drains); per-event block receives an `NIO::Monitor`.
**Data Shape:** `@io_selector` (nio4r); `buffers` = Hash defaulting to binary String, keyed by IO; `monitor.value` carries the Client; lines split on `\n`, reads capped at 10 240 bytes.

### Decisive source
```ruby
# STARTTLS swap after the client's command was accepted:
if !eof && client.start_tls?
  @io_selector.deregister(io)
  buffers.delete(io)                       # plaintext buffer is discarded, not carried over
  io = OpenSSL::SSL::SSLSocket.new(io, ssl_context)
  io.sync_close = true                     # closing TLS socket closes the TCP socket too
  monitor = @io_selector.register(io, :r)
  monitor.value = client                   # client object survives the socket swap
end

# handshake completes asynchronously:
if client.start_tls?
  begin
    io.accept_nonblock
    client.start_tls = false
  rescue IO::WaitReadable, IO::WaitWritable then next    # try again on next selectable event
  rescue OpenSSL::SSL::SSLError then eof = true          # failed handshake == disconnect, not exception
  end
end

# shutdown is DRAIN-based, not signal-based:
@io_selector.deregister(io); buffers.delete(io); io.close
if @io_selector.empty? then Process.exit(0) end           # also fired from unlisten + error paths
```

**Flow:** select → accept branch registers client (banner deferred under proxy protocol) → data branch reads ≤10 KiB, drains every complete buffered line through `client.handle(line)` writing returned replies with `\r\n` → STARTTLS swaps and re-registers the socket mid-loop → EOF/reset/write-failure or `client.finished?` closes that client → when nothing remains registered (`@io_selector.empty?`) the whole process exits, so each forked process owns its connections for life.
**Invariant:** the client object is attached to whichever IO is currently registered, so TLS upgrade is invisible to protocol state; plaintext leftovers are dropped at the swap boundary (never parsed post-TLS); any per-client exception tears down only that socket and re-checks emptiness; `::ffff:` IPv4-mapped prefixes are stripped at accept so IP checks see canonical addresses.
**Probe:** no dedicated spec file exists for `server.rb` in this repo — coverage caveat recorded; behavior is pinned indirectly by `spec/lib/smtp_server/client/*_spec.rb` driving `client.handle(...)` directly. Verify this gap before relying on loop-level claims.
**Coverage caveat:** `check_index_coverage(project: "postal", paths: ["app/lib/smtp_server/server.rb", ...])` ⇒ all `no_recorded_issue`/`metadata_match` (2026-08-25T20:10:23Z generation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.server.SMTPServer.Server.run_event_loop" });
```

## Verdict
Adopt selector-owned clients with monitor.value, drop-buffer-on-TLS-swap, nonblock handshake resumption, and empty-selector process exit as the graceful-shutdown mechanism for fork-per-process servers. Adapt nio4r to your event library. Omit Process.exit if your host supervises differently — but keep "exit only when truly idle".
