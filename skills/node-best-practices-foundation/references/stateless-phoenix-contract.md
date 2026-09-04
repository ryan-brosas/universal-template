<!-- capsule-v2 -->
# Stateless phoenix contract — which local-state patterns break a kill-and-replace server lifecycle?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What exactly must NEVER live on a single server's local disk/memory if servers are replaced routinely?

## Three named anti-patterns: multer disk uploads, file/memory session stores, global-object caches
**Path/Symbol:** `sections/production/bestateless.md` (:7 phoenix premise, :10-12 scaling/maintenance payoff, :17-33 the three mistakes).
**Signature:** ❌ `multer({ dest: 'uploads/' })`; ❌ `session({ store: new FileStore(options) })` (or default MemoryStore); ❌ `Global.someCacheLike.result = {...}`.
**Data Shape:** uploaded files, authenticated sessions, memoized results — each written to a location scoped to ONE process/host lifetime.

### Decisive source
```javascript
// bestateless.md :17-33 — the complete anti-pattern set
// Typical mistake 1: saving uploaded files locally on a server
const upload = multer({ dest: 'uploads/' });
// Typical mistake 2: storing authentication sessions (passport) in a local
// file or memory
const FileStore = require('session-file-store')(session);
// Typical mistake 3: storing information on the global object
Global.someCacheLike.result = { somedata };
```

**Flow:** servers are treated "like a phoenix bird – it dies and is reborn periodically without any damage" (:7) → horizontal scale means request N and N+1 may hit different replicas → any asset stored locally is unreachable to every OTHER replica and lost on replacement.
**Invariant:** a server is disposable hardware executing your code; NOTHING may exist only on it. Files → object storage; sessions → external shared store (pairs with `jwt-revocation-blacklist`: revocation shares the SAME external-store requirement); caches → shared cache tier. If any of the three anti-patterns is present, rolling deploys and autoscaling silently corrupt user state.
**Probe:** no runner upstream. Deterministic probe: `grep -cF 'Typical mistake' sections/production/bestateless.md` = 3 && `grep -c multer sections/production/bestateless.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "multer", limit: 5 });`

## Verdict
Adopt the three-pattern ban as a review checklist and the phoenix lifecycle as a design premise. Adapt storage backends per platform (S3/GCS, Redis, memcached). Omit nothing — the contract is the absence of local-only state.
