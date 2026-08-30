<!-- capsule-v2 -->
# Env-var strip allowlists — SAFE_ENV_VARS / ANT_ONLY split

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which `VAR=value` prefixes may be stripped before permission-rule matching, and how do you keep convenience strippings from defeating prefix restrictions?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashPermissions.ts` — `SAFE_ENV_VARS` (:378-440), `ANT_ONLY_SAFE_ENV_VARS` (:447-498) gated by `process.env.USER_TYPE === 'ant'`, `BINARY_HIJACK_VARS = /^(LD_|DYLD_|PATH$)/` (:708), consumers: `getSimpleCommandPrefix` (:161-190), `getFirstWordPrefix` (:243-283), `extractPrefixBeforeHeredoc` fallback, `stripSafeWrappers` Phase 1.
**Signature:** `ENV_VAR_PATTERN = /^([A-Za-z_][A-Za-z0-9_]*)=([A-Za-z0-9_./:-]+)[ \t]+/` — unquoted values, safe punctuation only, HORIZONTAL trailing whitespace only.
**Data Shape:** name-keyed Sets consulted at every prefix-suggestion site.

### Decisive source
```ts
// SECURITY: These env vars are stripped before permission-rule matching, which
// means `DOCKER_HOST=tcp://evil.com docker ps` matches a `Bash(docker ps:*)`
// rule after stripping. This is INTENTIONALLY ANT-ONLY (gated at line ~380)
// and MUST NEVER ship to external users. DOCKER_HOST redirects the Docker
// daemon endpoint — stripping it defeats prefix-based permission restrictions
```

**Flow:** a command's leading `VAR=val` tokens are stripped ONLY if the name is in SAFE_ENV_VARS (or the ant-only set under USER_TYPE); ANY other var ⇒ return null / stop stripping so the rule falls back to exact match — this prevents generating `Bash(npm run:*)` suggestions that can NEVER match at check time (strip-time and check-time must agree). The forbidden classes are documented in-place (:362-370): never PATH/LD_PRELOAD/DYLD_* (execution+library loading), PYTHONPATH/NODE_PATH/CLASSPATH (module loading), GOFLAGS/RUSTFLAGS/NODE_OPTIONS (code-exec flags), HOME/TMPDIR/SHELL/BASH_ENV (system behavior). `BINARY_HIJACK_VARS` catches the loader-prefix family for cd/git normalization. Ant-only additions are convenience strippings chosen from 30 days of internal telemetry but each one weakens a prefix restriction by construction — hence the hard user-type gate.

**Invariant:** (1) Strip-allowlist membership is a SECURITY decision: stripping makes `VAR=x cmd` rule-match as `cmd`, so any var that redirects an endpoint, loads code, or changes lookup paths is banned regardless of convenience. (2) Suggestion generation must use the SAME allowlist as matching — otherwise you mint dead rules or, worse, rules broader than what checks enforce. (3) Value charset is allowlisted (`[A-Za-z0-9_./:-]`) so `$(...)`, backticks, separators can't ride inside a stripped value; horizontal-only whitespace keeps newline-separated commands from merging into one strip. (4) Convenience-vs-external safety resolves to a user-type gate, not a second weaker list shipped broadly.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'MUST NEVER ship to external users' src/tools/BashTool/bashPermissions.ts` → :439; `grep -nF 'can contain code execution flags' src/tools/BashTool/bashPermissions.ts` → :375; `grep -nF 'BINARY_HIJACK_VARS' src/tools/BashTool/bashPermissions.ts | head -1` → :708; graph `search_graph --project locoagent --query getSimpleCommandPrefix getFirstWordPrefix` → :161-190 / :243-283.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SAFE_ENV_VARS ANT_ONLY_SAFE_ENV_VARS BINARY_HIJACK_VARS ENV_VAR_PATTERN", limit: 5 });
```

## Verdict
Adopt the two-list design with its explicit banned-classes doc comment; re-derive membership per product surface. Never strip an endpoint-redirecting or code-loading variable for external users.
