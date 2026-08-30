<!-- capsule-v2 -->
# Black-Box Script Discipline — when should the model invoke bundled scripts without reading them?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** How does a skill keep large helper scripts from polluting the model's context while still being used reliably?

## --help first, invoke directly, never ingest
**Path/Symbol:** `skills/webapp-testing/SKILL.md` (header rule + "Best Practices"); same doctrine in skill-creator's repeated-work rule ("If all 3 test cases resulted in the subagent writing a `create_docx.py` ... that's a strong signal the skill should bundle that script").
**Signature:** `python scripts/with_server.py [--server CMD --port N]... [--timeout S] -- <automation.py>`; readiness via `is_server_ready(port, timeout=30)` socket-polling (0.5s interval) on localhost.
**Data Shape:** Scripts are CLIs: usage discoverable via `--help`, inputs via flags, outputs to files/stdout — no source reading required.

### Decisive source
```markdown
**Always run scripts with `--help` first** to see usage. DO NOT read the source
until you try running the script first and find that a customized solution is
absolutely necessary. These scripts can be very large and thus pollute your
context window. They exist to be called directly as black-box scripts rather
than ingested into your context window.
...
❌ **Don't** inspect the DOM before waiting for `networkidle` on dynamic apps
✅ **Do** wait for `page.wait_for_load_state('networkidle')` before inspection
```

**Flow:** Task needs a complex workflow (server lifecycle, doc conversion, GIF assembly, MCP connection) → check bundled `scripts/` first → `--help` → invoke as black box with flags → only if the script genuinely cannot do it, read source and customize. Companion pattern for browser automation: navigate → wait networkidle → THEN screenshot/DOM-inspect → act on discovered selectors (reconnaissance-then-action).
**Invariant:** Context economy is a design constraint: a script that exists must be preferred over re-deriving its behavior; the exception path (reading source) is gated on demonstrated failure. For dynamic webapps, pre-networkidle inspection yields stale/incomplete DOM — the wait is part of the recon contract.
**Probe:** `python skills/webapp-testing/scripts/with_server.py --help` prints full usage without executing servers; running it with `--server "sleep 30" --port 5173 -- true` shows port-poll readiness then cleanup. Source is 50+ lines yet usage was obtained with zero context cost.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "with_server black-box scripts", limit: 10 });
```

## Verdict
Adopt: bundle deterministic/repeated workflows as flag-driven scripts and mandate help-then-invoke; gate source-reading behind failure; pair browser automation with networkidle-before-recon. Adapt to your harness's process-spawn conventions. Omit Playwright specifics if using another driver. Caveat: behavioral doctrine pinned by prose + one runnable script; no unit tests upstream.
