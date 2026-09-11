<!-- capsule-v2 -->
# Least-privilege drop + root-then-su-exec — how does the container run a stateful Java server as UID 200 while still preparing its volume as root?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does the image keep the server process non-root while allowing one-time root-only volume preparation?

## Root prep → non-root exec split
**Path/Symbol:** `Dockerfile:1-7` (image layers), `entrypoint.sh:4-9` (prep vs exec).
**Signature:** Dockerfile directives; `apk add --no-cache su-exec`; `COPY entrypoint.sh /usr/local/bin/nexus-railway-entrypoint` + `chmod +x`; `EXPOSE 8081`; JSON-form `ENTRYPOINT` (exec form — no shell wrapper, signals reach PID 1 directly).

### Decisive source
```dockerfile
FROM docker.io/sonatype/nexus3:3.95.2-alpine@sha256:adb4539e29bcb1c91e5545c853f6c74da5e57efd4c243aa4d5454f309904ab13
USER root
RUN apk add --no-cache su-exec
COPY entrypoint.sh /usr/local/bin/nexus-railway-entrypoint
RUN chmod +x /usr/local/bin/nexus-railway-entrypoint
EXPOSE 8081
ENTRYPOINT ["/usr/local/bin/nexus-railway-entrypoint"]
```

**Flow:** pin upstream image by digest (never `:latest` — `tests/static.mjs` asserts both) → re-enter root explicitly (`USER root`, because the base image's default USER is 200, so this is required to install packages and chown the volume) → add only `su-exec` → bake entrypoint at fixed path → exec-form entrypoint.
**Invariant:** the Nexus JVM itself NEVER runs as root. Root does exactly three things — `mkdir -p /nexus-data`, `chown -R 200:200 /nexus-data`, and (on restarts) nothing else before `exec su-exec nexus …` replaces the shell. The marker file gets an explicit `chown 200:200` (:22) because `touch` ran as root and a root-owned marker inside the app-owned volume breaks ownership symmetry on restored volumes. A porter who drops the `chown -R 200:200` gets an unbootable server on a fresh volume (JVM cannot write its data dir); a porter who leaves the server running as root defeats the entire design.
**Probe:** `tests/static.mjs` pins digest-pin format `/nexus3:3\.95\.2-alpine@sha256:[a-f0-9]{64}/` and absence of `:latest`. Deterministic probe: `grep -c 'chown' entrypoint.sh` ≥ 2. Runtime caveat recorded (no in-repo runtime harness). ERRATUM pass 5 (deepening-B lane): this Probe previously cited the pre-drift `3\.95\.1` regex from the pass-1 pin; re-derived against live source at 18e177a6 which asserts `3\.95\.2`.
