<!-- capsule-v2 -->
# CLI startup ladder — ordering is the protection, and stdout belongs to the protocol

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How does a single entry point order config, logging, a destructive-root claim, subcommand dispatch, and server construction so that every refusal arrives BEFORE the damage it prevents — while keeping stdout clean for a JSON-RPC host?

## main() — the ordered ladder in cli_main.py
**Path/Symbol:** `linkedin_mcp_server/cli_main.py` — `main` (:445-635), `_exit_on_a_bad_setting` (:422-430), `_obtain_shared_owner` (:313-389), `choose_transport_interactive` (:57-76); predicate `linkedin_mcp_server/daemon.py:daemon_would_be_used` (:246-271).
**Signature:** `main() -> None`; `_exit_on_a_bad_setting(error: ConfigurationError) -> NoReturn`; `_obtain_shared_owner(config: AppConfig) -> DaemonProxyBackend | None`.
**Data Shape:** One `AppConfig` from `get_config()` threads the whole ladder; subcommands (`--logout`, `--import-from-browser`, `--login`, `--status`) each exit; otherwise the process becomes an MCP server (direct or PROXY role).

### Decisive source
```python
# :422-430 — a bad setting names itself; logging is configured FROM the config
# that may have failed, so it cannot be the reporter, and stdout is the protocol
def _exit_on_a_bad_setting(error: ConfigurationError) -> NoReturn:
    print(f"❌ Configuration error: {error}", file=sys.stderr)
    sys.exit(1)

# :488-491 — the claim reads the config already in hand, NOT the global helper
# that lazily re-parses sys.argv
ensure_profile_claim(
    Path(config.browser.user_data_dir),
    claim_anyway=config.server.claim_profile_root,
)

# :540-546 — the interactive answer is written back into the stored config and
# re-validated, because later checks read the STORED transport
config.server.transport = transport
try:
    config.validate()
except ConfigurationError as e:
    _exit_on_a_bad_setting(e)

# :252-260 — who is even a candidate for sharing a browser
if not config.server.daemon_enabled:
    return False
if config.server.transport != "stdio":
    return False
```
**Flow:** get_config → login-viewer preflight → ConfigurationError ⇒ stderr + exit(1), never a traceback → configure_logging → banner (interactive only) → configure_browser_environment → **ensure_profile_claim before anything touches the root** (logout deletes it, browser install downloads into it, daemon election spawns an owner that re-checks) → set_headless → subcommand dispatch (each exits) → transport prompt (interactive, non-explicit only) → `_obtain_shared_owner` → create_mcp_server (direct, or role=PROXY with the elected backend) → mcp.run. For HTTP: `host_origin_protection=True`, no `allowed_hosts`.
**Invariant:** Every destructive or downloading step runs AFTER the profile-root claim, and the claim is read off the config already in hand — reaching for the global config again would re-parse whatever `sys.argv` holds. Diagnostics go to stderr because stdout is parsed as JSON-RPC by the stdio host; a diagnostic there corrupts the stream it explains. The interactive transport answer must land in the STORED config (not a local): the bind-address warning, the cookie-import exposure gate, and the daemon election all read it — an interactively chosen HTTP server must not elect a detached owner. `_obtain_shared_owner` is never fatal by decision: a client that refused to start would fail where nobody reads the reason; the fallback warning is the only thing that says the feature was lost. `host_origin_protection=True` rather than `"auto"` (auto validates only loopback arrivals, so an exposed bind checked nothing — measured: attacker Host+Origin over the LAN address were served, same request to 127.0.0.1 refused), and no host wildcard (a wildcard accepts the attacker's Host and reopens the hole from the other side).
**Probe:** `tests/test_cli_main.py` — `TestTheProfileRootIsClaimedBeforeAnythingTouchesIt` (:619-753) pins claim-before-logout ordering, refusal-exits-without-traceback, and the real-startup case where nothing is stubbed; `TestForwardingToASharedOwner` (:792-985) pins off-by-default, HTTP-never-elects, election-result-hands-back, raising-election-never-fatal, and "an HTTP server must not elect a daemon"; `TestConfigurationErrorAtStartup` (:986-1053) pins stderr-only, no Traceback, stdout empty; `test_main_streamable_http_enables_host_and_origin_validation` (:199-227) pins `host_origin_protection is True` and absence of `allowed_hosts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "cli_main main ensure_profile_claim obtain_shared_owner transport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder shape for any entry point that mixes a protocol-clean stdout, a destructive-root guard, and optional shared-resource election: claim-before-touch, config-in-hand (never re-parse argv mid-startup), write interactive answers back into stored state that later gates read, and make opt-in resource sharing fail soft with a warning that carries the trade. Adapt the subcommand set and the HTTP protection flag to your transport's spec. Omit the LinkedIn-specific banner/emoji UX. Coverage caveat: none — cli_main.py and test_cli_main.py fully indexed at the pin (no_recorded_issue); graph unavailable this pass, citations verified by direct read.
