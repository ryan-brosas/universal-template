<!-- capsule-v2 -->
# CLI Command Surface & Session Helper — thin argparse shells over service calls

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** What is the shape of each operator command so future passes can adjudicate them as product-shell without re-mining?

## One module per command; _session owns connection resolution + AsyncSession lifecycle
**Path/Symbol:** `packages/python/awaithumans/cli/commands/` — add_user, bootstrap_operator, create_service_key, list_service_keys, revoke_service_key, list_users, remove_user, set_password, doctor, serve, version, dev, `_session.py` (:1-35); entry `cli/main.py` subcommand registry.
**Signature:** each module exposes a small `async def run(...)`/handler wired by main; `_session.with_session()` yields an AsyncSession resolved via utils/discovery precedence (explicit arg → env → discovery file → default URL).
**Data Shape:** commands are 30–80-line wrappers calling the SAME service functions the routes use (service_key_service, user_service, bootstrap) — zero duplicated business logic.

### Decisive source
```python
# cli/commands/_session.py — the only non-trivial shell primitive:
# resolves server URL/admin token through discovery (see dev-discovery-file
# capsule) and yields a session so commands share route-layer semantics.
```
`serve` delegates to uvicorn app factory; `doctor` runs the lazy staged health checks surfaced in the dashboard; `bootstrap_operator` prints the one-shot token DIRECTLY to stdout (banner survives pipes — covered by bootstrap-token-error-taxonomy).

**Flow:** operator runs `awaithumans <cmd>` → main dispatches → command resolves session → calls service function → prints human/table output. No command contains crypto, SQL, or status logic of its own.
**Invariant:** the CLI layer must stay logic-free; anything reusable belongs in services so routes and commands cannot drift.
**Probe:** graph pins e.g. `create_service_key` CLI wrapper rank-3 (:19-46) beside its service twin rank-4 — the pairing itself demonstrates the thin-shell rule; suites under tests/cli/ green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "cli commands with_session doctor serve bootstrap_operator", limit: 6 });
```

## Verdict
Adopt the thin-shell-over-services rule and shared session helper; adapt command sets freely. This capsule exists to keep future passes from re-auditing these files — contracts live in the service capsules they wrap.
