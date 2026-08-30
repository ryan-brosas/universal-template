<!-- capsule-v2 -->
# Email Transport Factory & SMTP Traps — port 465 defaults and the username/user alias

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does one factory serve env-configured AND per-identity DB transports — and which two silent SMTP misconfigurations did it have to make loud?

## resolve_transport(name, config) single entry; None-means-skip at the resolve_* layer
**Path/Symbol:** `packages/python/awaithumans/server/channels/email/transport/factory.py` — docstring (:1-12), `resolve_transport` (:35-88), `resolve_default_transport` (:91-115), `resolve_identity_transport` (:118-131).
**Signature:** `resolve_transport(name: str, config: dict) -> EmailTransport` (raises EmailTransportError on unknown/missing); both `resolve_*` wrappers return None on missing config or EmailTransportError so the notifier logs-and-skips instead of raising.
**Data Shape:** transports: resend{api_key}, smtp{host, port=587, username|user, password, use_tls, start_tls=True}, logging{}, noop{}, file{dir}.

### Decisive source
```python
# Accept `user` as an alias for `username`. The dashboard's Email-identity form
# hint advertises `user`, Python's stdlib smtplib uses `user` too — silently
# dropping it left users with unauthenticated SMTP and no signal.
username = config.get("username") or config.get("user")
# Port 465 is implicit-TLS; default use_tls to True there unless explicitly
# overridden. STARTTLS on 465 fails the handshake, which is the exact trap most
# operators hit on the first send.
use_tls = bool(config["use_tls"]) if "use_tls" in config else port == 465
```
Explicit keys win over defaults (`test_factory_smtp_explicit_use_tls_overrides_port_default`:150); explicit `username` beats `user` when both present (:115).

**Flow:** notifier needs a transport → identity route? decrypt config via identity_config → resolve_identity_transport; else env vars → resolve_default_transport → both funnel into resolve_transport → unknown name raises with the VALID list in the message. Errors inside resolve_* are logged-and-None'd (visible via notification_failed audit).
**Invariant:** the factory RAISES (typed, actionable), the resolvers SWALLOW-to-None — keeping raise-vs-return discipline split between construction and resolution layers.
**Probe:** `packages/python/tests/email/test_transport.py` (`test_factory_smtp_accepts_user_alias_for_username`:97, `test_factory_smtp_port_465_defaults_use_tls_true`:130, `test_factory_smtp_port_587_defaults_use_tls_false`:142, `test_factory_unknown_transport_raises`:70, `test_noop_send_returns_id`:164) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "resolve_transport resolve_default_transport smtp use_tls 465", limit: 4 });
```
Live rank-4 line-exact (:91-115) with the 465/587 default tests ranked above it.

## Verdict
Adopt the two-layer raise/swallow split and BOTH SMTP traps (465-implicit-TLS default, user/username alias); adapt transport set to your providers; omit the file transport only if you don't need local dev capture.
