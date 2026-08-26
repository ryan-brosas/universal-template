<!-- capsule-v2 -->
# URL.replace netloc reassembly — how do I mutate one authority component without destroying userinfo, ports, or IPv6 literals?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** Why does replacing a single component like `port` require hand-rebuilding the netloc instead of trusting `SplitResult._replace`?

## replace()
**Path/Symbol:** `starlette/datastructures.py:URL.replace` (:115-141).
**Signature:** `def replace(self, **kwargs: Any) -> URL`.
**Data Shape:** kwargs may carry any SplitResult field; if ANY of {username, password, hostname, port} is present, the netloc is rebuilt manually before delegating.

### Decisive source
```python
if "username" in kwargs or "password" in kwargs or "hostname" in kwargs or "port" in kwargs:
    hostname = kwargs.pop("hostname", None)
    port     = kwargs.pop("port", self.port)          # defaults PRESERVE current values
    username = kwargs.pop("username", self.username)
    password = kwargs.pop("password", self.password)
    if hostname is None:
        netloc = self.netloc
        _, _, hostname = netloc.rpartition("@")       # strip existing userinfo
        if hostname and hostname[-1] != "]":          # IPv6 literal: DON'T split on ':'
            hostname = hostname.rsplit(":", 1)[0]     # strip old port
    netloc = hostname
    if port is not None:      netloc += f":{port}"
    if username is not None:
        userpass = username + (f":{password}" if password is not None else "")
        netloc = f"{userpass}@{netloc}"
    kwargs["netloc"] = netloc
components = self.components._replace(**kwargs)
return self.__class__(components.geturl())
```

**Flow:** authority-touching replace → pop the four fields with CURRENT values as defaults → reassemble netloc host→`:port`→`user[:pass]@` → hand the netloc to `SplitResult._replace` → render via geturl into a fresh URL. Non-authority replaces (scheme, path, query, fragment) skip straight to `_replace`.
**Invariant:** unspecified authority components survive verbatim — `replace(hostname="bar")` on `http://u:p@host/` keeps `u:p@`; `replace(port=88)` keeps userinfo; `replace(username="u")` keeps an existing port. The `[-1] != "]"` guard is what stops `[fe::2]:123` from being colon-split at its last address colon. Authority components added to a no-authority URL synthesize a relative-netloc (`//:8080/path?a=1`) rather than raising.
**Probe:** `tests/test_datastructures.py::test_url` (:31-69 — scheme/port/hostname swaps, IPv6 port + userinfo replaces :43-53, userinfo preservation :55-62, authorityless gain :64-69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "^replace$", filePattern: "*datastructures*", limit: 5 });
```

## Verdict
Adopt the four-field default-preservation ladder and the IPv6 bracket guard byte-for-byte — naive `netloc.rsplit(":")` corrupts every IPv6 host. Adapt which components you expose for mutation. Omit userinfo support entirely only if you reject userinfo URLs at your edge (then the whole userpass branch collapses). Note this is the mutation twin of masked-repr-hygiene's `replace(password="********")` — same code path, different consumer.
