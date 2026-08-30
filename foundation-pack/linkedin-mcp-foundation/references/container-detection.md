<!-- capsule-v2 -->
# Container detection — which signals may decide "am I in a container"?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you detect a container runtime without misdetecting workstations that merely run Docker, and how should the heuristic fail?

## Only signals describing OUR process count
**Path/Symbol:** `linkedin_mcp_server/session_state.py:_is_container_runtime()` (:173-410); feeds `get_runtime_id()`.
**Signature:** `_is_container_runtime() -> bool`; override env `LINKEDIN_MCP_CONTAINER=true/false` wins over everything.
**Data Shape:** Reads `/proc/self/cgroup`, `/proc/self/mountinfo`; returns bool; unreadable/ambiguous → False (host) because the dangerous direction differs per consumer.

### Decisive source (the post-mortem rules)
```text
- Substring search for "docker" matched workstations merely RUNNING Docker
  daemons → permanent unrecoverable misdetection. Whole path SEGMENTS only:
  {docker, containerd, kubepods, podman, machine, moby}; skip
  .service/.socket/.mount suffixes (docker.service IS the host's daemon);
  systemd escapes dashes so app-docker\x2ddesktop.scope un-escapes to a
  desktop app.
- Instance-id regex ^(libpod-|crio-|docker-|containerd-)[0-9a-f]{32,}$ —
  32 hex MINIMUM: runtimes write full 64-char ids, no hand-named service
  reaches that (docker-backup.scope was once misread as a container).
- LXC/nspawn named prefixes (lxc.payload., machine-) kept separate from id
  regexes since they carry arbitrary user text.
- Mount ROOT, never mount source: compare rootfs layouts against the
  kernel-reported mount root; an NFS source label describes somebody else's
  namespace. Network filesystems skipped entirely.
- Deliberately ignored: /run/systemd/container — OrbStack reports "lxc" yet
  is a full desktop-class system.
```
**Flow:** env override (unreadable value → warn + fall through to detection; "an unreadable value is not a decision") → cgroup segment classification → instance-id regex → LXC prefixes → mount-root check → verdict.
**Invariant:** Heuristic environment detection must be written as measured post-mortems of REAL misdetections, conservative toward the dangerous direction (here: false-negative container = browser looks for a keychain that isn't there), and always overridable by an explicit env flag.
**Probe:** `tests/test_session_state.py` container-detection cases pin segment matching and escape handling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_is_container_runtime cgroup container detection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the signal-epistemology rules verbatim for any container/host branching. Adapt the segment set to your runtimes. Omit LinkedIn specifics.
