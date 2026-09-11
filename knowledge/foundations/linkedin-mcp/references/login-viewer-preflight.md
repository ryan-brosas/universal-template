<!-- capsule-v2 -->
# Login-viewer preflight — which container mounts make a persisted login impossible?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** Before starting a login whose result must outlive the container, which filesystem conditions must be refused and how?

## Refusals name their remedy; tmpfs fails the same test as no mount
**Path/Symbol:** `linkedin_mcp_server/login_viewer.py` (`mount_records` :47, `_remedy` :75, `require_persistent_profile_mount` :82, `_require_a_writable_auth_root` :142); supervision class :181-357.
**Signature:** `require_persistent_profile_mount(mountinfo_text, *, auth_root, profile)` → raises with inline remedy or passes; `VIEWER_WALL_SECONDS = 1800`.
**Data Shape:** Parses `/proc/self/mountinfo` text defensively — optional-tag fields searched FROM INDEX 6 so a mount point literally spelled `-` isn't mistaken for the separator; octal escapes decoded (`_decode_mount_field` :42).

### Decisive source (the preflight decisions)
```text
- Mount-on-profile is WORSE than no mount: session rotation MOVES the
  profile directory aside, but a mountpoint cannot move — shutil.move
  falls back to copy-then-delete across devices, duplicating then emptying
  the session before EBUSY. Refusal says exactly what to mount instead
  (the auth ROOT), via _remedy(): a literal -v ~/.linkedin-mcp:... flag.
- Nearest covering mount only: an ancestor further up describes a
  different filesystem once something closer mounts over it.
- tmpfs/ramfs FAILS THE SAME TEST as no mount: "a filesystem held in RAM
  answers every question a bind mount answers… it still loses the session
  when the container stops."
- Write permission checked BEFORE rotation: Docker seeds named volumes
  root-owned; discovering unwritability on first write happens AFTER the
  previous session moved aside. Error includes uid/gid and a literal
  `sudo chown` command.
```
**Flow:** parse mountinfo → find nearest covering mount of auth root → classify (none / on-profile / tmpfs-ramfs / network fs) → refusal WITH exact remedy string → writable check (as effective uid) → then and only then start viewer stack.
**Invariant:** A preflight that will die with the container must refuse BEFORE destroying prior state; every refusal carries the exact fix inline because diagnosis-at-failure-time is too late for auth state. mountinfo parsing must tolerate hostile field values.
**Probe:** `tests/test_login_viewer.py` pins remedy strings and mount classifications.

## Token-private noVNC exposure
**Path/Symbol:** `linkedin_mcp_server/login_viewer.py` supervision (`start_window_manager` :189, `start_remote_control` :208, teardown :260-357).
**Data Shape:** Openbox → x11vnc (loopback-only: `-listen 127.0.0.1 -allow 127.0.0.1 -no6`, `-nopw`) → websockify with ReadOnlyTokenFile; token = `secrets.token_urlsafe(32)`, written `O_WRONLY|O_CREAT|O_EXCL` mode 0o600 in a 0o700 temp dir.

### Decisive source
```text
Layered readiness: each component gets a per-component LOG FILE;
_require_alive polls after every start; _wait_for_port polls TCP 0.1s×100;
openbox readiness = obxprop --root _NET_SUPPORTING_WM_CHECK actually
ANSWERING (not just process-alive). Failure messages APPEND THE COMPONENT
LOG — diagnosis ships with the error. Teardown removes exposure in
REVERSE order (websockify → x11vnc → openbox), attempts EVERY layer even
after one fails (first exception preserved), deletes credential file +
temp dir in finally.
```
**Flow:** preflight → WM → VNC → websockify → emit token-private URL (valid VIEWER_WALL_SECONDS) → teardown reverse ladder.
**Invariant:** Security gate lives at ONE layer (websockify token file) so inner layers stay passwordless-local; readiness = functional probe not process existence; failures carry their logs.
**Probe:** `tests/test_login_viewer.py` pins layered startup/teardown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "require_persistent_profile_mount viewer_url websockify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt remedy-naming preflights + reverse-order teardown with per-component logs for any supervised local service stack. Adapt mount rules to your storage. Omit noVNC specifics if unused.
