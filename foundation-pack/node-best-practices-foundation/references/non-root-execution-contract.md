<!-- capsule-v2 -->
# Non-root execution contract — the two forces that push Node back to root, and both counter-moves

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why does your container silently run as root, and what's the least-privilege shape?

## Listen unprivileged + reverse-proxy for <1024; USER node in Dockerfile
**Path/Symbol:** `sections/security/non-root-user.md` (root-forces :5-8, Dockerfile example :12-21, docker-node quote :27-28).
**Signature:** Dockerfile `USER node` before CMD; app listens on >=1024 (e.g. 3000); proxy (nginx/HAProxy) owns 80/443.
**Data Shape:** node images ship a pre-created unprivileged `node` user — `-u node` or `USER node` adopts it.

### Decisive source
```dockerfile
# non-root-user.md :12-21 — the minimal compliant image tail
FROM node:latest
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
USER node
CMD ["node", "server.js"]
```

**Flow:** two legit-looking reasons drag apps to root (:5-8): binding privileged ports (<1024) and Docker's default root runtime ("Docker containers by default run as root(!)", :8). Both have structural fixes: reverse-proxy terminates 80/443 and forwards to the unprivileged app port; orchestrators (Swarm/K8s) let you declare the security context instead of baking root in.
**Invariant:** THE MISS: forgetting `USER` placement — anything after it runs as node, everything before (npm install writing node_modules) legitimately needed root; putting `USER node` first breaks installs, omitting it leaves the exploit blast radius at "total control over your machine" (Lalonde quote :34-35). Root inside the container ≈ root on the host unless additional isolation exists — least privilege is the cheap half of that defense.
**Probe:** no runner upstream. Deterministic probe: `grep -c '^USER node' sections/security/non-root-user.md` >= 1 && `grep -c 'reverse-proxy' sections/security/non-root-user.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "reverse-proxy", "limit": 10}'
# resolves `sections/security/non-root-user.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt `USER node` + unprivileged listen as image-review checklist items; pair with `multi-stage-build-and-secrets` (docker section capsule) for the full hardening stack. Adapt UID management on platforms without a shipped user. Omit iptables port-forwarding in favor of proxies unless proxyless.
