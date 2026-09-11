<!-- capsule-v2 -->
# Node-direct bootstrap — why does `CMD ["npm","start"]` break graceful shutdown and leave zombies?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you start Node in a container so PID1 is Node (or a signal-forwarding init), not a shell or npm?

## exec-form node, or TINI as PID1 when spawning children
**Path/Symbol:** `sections/docker/bootstrap-using-node.md` (explainer :1, node form :9-14, TINI form :16-27, anti-patterns :29-43, process tree :68-73) + `sections/docker/graceful-shutdown.md` (Dockerfile :7-11, TINI :13-25, npm anti-pattern :27-31).
**Signature:** `CMD ["node", "server.js"]` (exec form) — never `CMD "node server.js"` (shell form) and never `CMD ["npm","start"]`.
**Data Shape:** the failure is a process-tree shape: `npm` (PID1) → `sh -c node server.js` → `node`. npm does not forward OS signals to the child, so SIGTERM never reaches Node → no graceful shutdown, and child processes aren't cleaned up → zombies (:1, :68-73).

### Decisive source
```dockerfile
# bootstrap-using-node.md :9-14 — correct
FROM node:12-slim AS build
WORKDIR /usr/src/app
COPY package.json package-lock.json ./
RUN npm ci --production && npm clean cache --force
CMD ["node", "server.js"]          # exec form → Node is PID1
# :16-27 — add TINI only if the app spawns child processes
ENTRYPOINT ["/tini", "--"]
CMD ["node", "server.js"]
```

**Flow:** container starts → exec-form CMD makes Node PID1 so it receives SIGTERM/SIGINT directly → graceful-shutdown handler runs. If the app spawns children, TINI as ENTRYPOINT reaps zombies and forwards signals while Node stays a sub-process.
**Invariant:** the bootstrap must not interpose a non-forwarding process (npm, or a shell from `CMD "node server.js"`) between the runtime and PID1. Node's own graceful-shutdown doc (:27-31) flags `CMD ["npm","start"]` as the anti-pattern because npm won't pass signals. Note: npm 7+ claims signal forwarding (README 8.2 update) — verify per toolchain version.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'sh -c node server.js' sections/docker/bootstrap-using-node.md` = 1 (the process-tree evidence).

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "sh -c node server.js", "limit": 10}'
# resolves `sections/docker/bootstrap-using-node.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt exec-form `node` bootstrap (and TINI when spawning children) for any containerized service. Adapt base image and runtime name. Omit npm-version signal claims — verify against your toolchain.
