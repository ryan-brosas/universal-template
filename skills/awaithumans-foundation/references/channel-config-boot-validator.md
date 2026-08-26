<!-- capsule-v2 -->
# Boot-Time Channel Config Validator — catch half-configured channels before the first silent drop

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** What does a server check at startup so an operator's forgotten credential becomes one WARNING instead of a mystery delivery failure?

## Per-channel required-var census; never raises; unknown transport surfaces too
**Path/Symbol:** `packages/python/awaithumans/server/core/channel_config_validator.py` — rationale (:1-15), `validate_channel_config` (:26-34), `_validate_email` (:37-82), `_validate_slack` (:85-110). Called once from `create_app()` after `setup_logging()`.
**Signature:** `validate_channel_config(settings: Settings) -> None`.
**Data Shape:** email transports: smtp requires {SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM}; resend requires {RESEND_KEY, EMAIL_FROM}; logging/noop need nothing; anything else warns unrecognized. Slack dual-mode: static mode needs SLACK_SIGNING_SECRET beside SLACK_BOT_TOKEN; OAuth mode needs {CLIENT_SECRET, SIGNING_SECRET, INSTALL_TOKEN} beside CLIENT_ID.

### Decisive source
```python
missing = [k for k, v in required.items() if not v]
if missing:
    logger.warning(
        "AWAITHUMANS_EMAIL_TRANSPORT=smtp is set but these env vars are missing: %s. "
        "SMTP sends will fail with %s until they're configured.",
        ", ".join(missing),
        "no_from_address" if missing == ["AWAITHUMANS_EMAIL_FROM"] else "transport_error",
    )
```
Slack static-mode warning names the CONSEQUENCE precisely: "Outbound messages will send, but inbound interactions will fail signature verification."

**Flow:** boot → validate_email then validate_slack → each partially-configured channel emits exactly ONE warning listing missing env-var NAMES and the failure code the send would produce → runtime continues (sends fail visibly via notification_failed audit — see notification-failure-audit capsule).
**Invariant:** NEVER raises — a partial config leaves the runtime functional; the warning predicts WHICH error string the notifier will emit, tying boot-time diagnostics to runtime behavior.
**Probe:** `packages/python/tests/core/test_channel_config_validator.py` (`test_smtp_transport_warns_when_host_missing`:109, `test_unknown_email_transport_emits_warning`:176, `test_slack_bot_token_without_signing_secret_warns`:187, `test_slack_oauth_partial_config_warns_about_missing_pieces`:205, `test_no_channels_configured_emits_no_warning`:231) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "validate_channel_config _validate_email _validate_slack", limit: 4 });
```
Live rank-1..3 line-exact.

## Verdict
Adopt the required-set census pattern and consequence-predicting warnings; adapt channel/transport names to your stack; omit the unknown-transport arm only if config parsing already rejects bad names earlier.
