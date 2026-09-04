<!-- capsule-v2 -->
# Daemon rendezvous key — why is the socket name the SAME for every build of the product?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What goes into the endpoint identity and — more importantly — what must never?

## FNV-1a over one domain string; version/path/cache/ABI excluded BY DESIGN
**Path/Symbol:** `src/daemon/service.c:cbm_daemon_rendezvous_key` (144–162) + header rationale (service.h:4–10) + test tests/test_daemon_version.c:201–216.
**Signature:** `bool cbm_daemon_rendezvous_key(char out[17]);`
**Data Shape:** Output: 16 lowercase hex chars (FNV-1a-64 of `"codebase-memory-mcp:coordination-daemon"`), format-checked by snprintf return. Deliberately EXCLUDED inputs: executable path, release version, build fingerprint, cache directory, ABI values.

### Decisive source
```c
/* This product-domain string is intentionally the only key input. Account
 * isolation comes from the authenticated IPC runtime, not spoofable text. */
/* service.h: The rendezvous key deliberately excludes executable path, release
 * version, build fingerprint, cache directory, and ABI values. Every stateful
 * CBM frontend for one OS account must meet at one endpoint; the HELLO
 * comparison then either admits the exact build or returns an explicit conflict. */
```

**Flow:** any frontend (old CLI, new daemon, hook) derives the identical key → connects to one endpoint per OS account → HELLO then sorts out compatibility → conflicts are diagnosable rather than silent parallel daemons.
**Invariant:** Adding ANY varying component to the key silently forks coordination across upgrades; isolation belongs to the OS-account runtime dir, never to the name.
**Probe:** `tests/test_daemon_version.c:daemon_rendezvous_key_is_stable_and_version_independent` asserts equality across an upgrade simulation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "rendezvous_key", limit: 5 });
```

## Verdict
Adopt stable-product-domain naming for shared endpoints with separate admission checks; adapt the domain string; this inversion (stable name + strict hello) is the whole pattern.
