<!-- capsule-v2 -->
# url-component-contract — How do you serve WHATWG-shaped URL components from a RFC-3986 parser?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** Which component-shaping rules must a porter replicate so `new URL()` behaves like the browser?

## URL handler component seam
**Path/Symbol:** `lib/quickbeam/url.ex:parse/1` (:15-28), `build_components/2` (:81-107), `format_port/2` (:109-113), `build_origin/3` (:132-142); recompose twin `do_recompose/1` (:162-173).
**Signature:** handler returns `%{"ok" => true, "components" => map}` or `%{"ok" => false, "error" => reason}` (never raises); components carry protocol+colon, lowercased hostname, port STRING ("" when default), search/hash WITH prefixes, `_port` integer-or-default escape hatch.
**Data Shape:** Backed by `:uri_string.parse/resolve/recompose` (RFC-3986 semantics) reshaped to WHATWG conventions.

### Decisive source
```elixir
path = if(host != "" and path == "", do: "/", else: path)      # empty path ⇒ "/"
port_str = case format_port(port, scheme_lower) do
  # :undefined → ""; port == scheme default → ""; else digits
end
%{
  "protocol" => scheme_lower <> ":",
  "hostname" => String.downcase(host),
  "pathname" => path,
  "search"   => prefix_if_present("?", query),
  "hash"     => prefix_if_present("#", fragment),
  "origin"   => build_origin(scheme_lower, host, port_str),  # special schemes only; else "null"
  "_port"    => if(port != :undefined, do: port, else: Map.get(@default_ports, scheme_lower))
}
```

**Flow:** trim input → base present ⇒ validate base then `:uri_string.resolve` (binary result required) → parse absolute → reshape into WHATWG components. Recompose is the inverse: strip prefixes, drop empties (`put_unless_empty`), feed back to `:uri_string.recompose`.
**Invariant:** (1) Default-port elision is load-bearing for origin equality (`http://x:80/` must equal `http://x/`) — @default_ports covers http/https/ftp/ws/wss. (2) Special-scheme gate on origin: anything else yields literal `"null"` like browsers do. (3) Hostname downcasing happens at component build, userinfo split parts:2 keeps passwords containing colons intact. (4) Errors are VALUES not raises because the JS side maps ok:false to a thrown TypeError itself.
**Probe:** `grep -c 'default_ports' lib/quickbeam/url.ex` → 3.
**Probe:** direct test `test/web_apis/new_web_apis_test.exs` pins URL behavior at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "url parse components origin default port", limit: 10 });
```

## Verdict
Adopt the RFC-parser-under-WHATWG-shaping approach and the exact elision rules; adapt to your host's URI library; omit file-scheme quirks unless you support them. Coverage: url.ex no_recorded_issue+metadata_match.
