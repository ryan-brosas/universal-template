# Configuration and operations

Use the schema and environment reference matching the deployed release. This is
a decision guide, not a frozen copy of the generated schemas. Complete source
coverage and known contradictions are in [the documentation map](documentation-map.md).

## Configuration ownership

`CONFIG_PATH` identifies a mounted config; Sourcebot syncs it at startup and when
changes are detected. Comments are supported. Top-level responsibilities are
`connections` (code hosts), `models` (LLMs), `contexts` (search groups), `settings`
(operations), `apps` (GitHub Apps), `identityProviders` (SSO/account linking) and
`environmentOverrides`. Follow the owning reference before changing one.

Secret fields accept `{ "env": "NAME" }` or
`{ "googleCloudSecret": "projects/<id>/secrets/<name>/versions/<version>" }`.
`environmentOverrides` values have `type` of `token`, `string`, `number` or
`boolean` and a `value`; they are resolved at startup into memory, **not exported
as process environment variables**. They cannot override `CONFIG_PATH`.

## Indexing and queue controls

| Config setting | Documented default / use |
| --- | --- |
| `maxFileSize`, `maxTrigramCount` | 2 MB / 20,000; larger documents are skipped |
| `reindexIntervalMs` | 1 hour; repository reindex cycle |
| `resyncConnectionIntervalMs` | 24 hours; connection discovery/visibility sync |
| `repoIndexTimeoutMs` | 2 hours; indexing timeout |
| `maxConnectionSyncJobConcurrency`, `maxRepoIndexingJobConcurrency` | 8 each; lower to reduce memory/CPU peaks |
| `maxAccountPermissionSyncJobConcurrency`, `maxRepoPermissionSyncJobConcurrency` | 8 each; permission-sync workload |
| `repoDrivenPermissionSyncIntervalMs`, `userDrivenPermissionSyncIntervalMs` | 24 hours each; access-update delay, not code freshness |
| `repoGarbageCollectionGracePeriodMs` | 10 seconds; protects shards while loading |

The published schema marks `resyncConnectionPollingIntervalMs`,
`reindexRepoPollingIntervalMs` and `maxRepoGarbageCollectionJobConcurrency`
deprecated even where prose tables still list their old 1-second/8 defaults.
Also replace deprecated `experiment_*PermissionSyncIntervalMs` names and
`enablePublicAccess` only using the installed release's supported policy
controls. Never turn on anonymous access as a migration shortcut.

`REDIS_REMOVE_ON_COMPLETE=0` and `REDIS_REMOVE_ON_FAIL=100` bound retained queue
jobs. `REPO_SYNC_RETRY_BASE_SLEEP_SECONDS=60` controls sync retry backoff;
`GITLAB_CLIENT_QUERY_TIMEOUT_SECONDS=600` controls GitLab query timeout. Diagnose
rate limits, transport and queued work before merely increasing these limits.

## Runtime and UI controls

- `DATA_DIR` defaults to `/data`; `DATA_CACHE_DIR` to `$DATA_DIR/.sourcebot`.
  Persistent paths and certificate/credential paths must exist **in the container**.
- v5 requires database/cache URLs and both persistent secrets; see
  [deployment](deployment-and-upgrades.md). `DATABASE_HOST`, `DATABASE_USERNAME`,
  `DATABASE_PASSWORD`, `DATABASE_NAME` and `DATABASE_ARGS` can construct the
  database URL; inspect precedence in the release before mixing forms.
- `DEFAULT_MAX_MATCH_COUNT=10000` is the web-search default cap, not a guarantee
  of exhaustive results. `DEFAULT_HOME_VIEW_PAGE=search` may be `ask` and applies
  when the user has no home-page preference.
- `ALWAYS_INDEX_FILE_PATTERNS` is a comma-separated glob override for skipped
  large/high-trigram files. It does not make binary files indexable.
- `SOURCEBOT_CHAT_ATTACHMENT_MAX_IMAGE_BYTES=10485760` limits each Ask image to
  10 MiB. `SOURCEBOT_CHAT_ATTACHMENT_ORPHAN_TTL_HOURS=24` expires uploaded but
  unsent attachments; `0` disables that sweep.
- `SOURCEBOT_PUBLIC_KEY_PATH=/app/public.pem` selects license-signature
  verification material; it is not a provider API key.
- Session/OAuth/API-key restrictions belong to
  [identity and permissions](identity-and-permissions.md); SMTP belongs to
  [administration](administration-and-licensing.md); review-agent controls belong
  to [Ask and agents](ask-models-and-agents.md).

## Network and Redis TLS

Node's `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` require `NODE_USE_ENV_PROXY=1`;
the default is `0`. Diagnose from inside Sourcebot's runtime, not just the host.
Prefer a trusted CA via `NODE_EXTRA_CA_CERTS` for self-hosted code hosts over
turning off TLS validation.

Use `REDIS_TLS_ENABLED=true` or a `rediss://` URL. The TLS controls are
`REDIS_TLS_CA_PATH`, `REDIS_TLS_CERT_PATH`, `REDIS_TLS_KEY_PATH`,
`REDIS_TLS_KEY_PASSPHRASE`, `REDIS_TLS_SERVERNAME` (SNI),
`REDIS_TLS_SECURE_PROTOCOL`, `REDIS_TLS_CIPHERS` and
`REDIS_TLS_HONOR_CIPHER_ORDER`. Keep `REDIS_TLS_REJECT_UNAUTHORIZED` at its secure
true default; do not set `REDIS_TLS_CHECK_SERVER_IDENTITY=false` to bypass host
identity checks. Disabling either verification
is a security change, not a normal certificate fix.

## Logs, analytics and outbound traffic

`SOURCEBOT_LOG_LEVEL` accepts `debug`, `info`, `warn`, `error`, default `info`.
`SOURCEBOT_STRUCTURED_LOGGING_ENABLED=true` selects JSON instead of human-readable
logs; `SOURCEBOT_STRUCTURED_LOGGING_FILE` optionally writes a file. Records expose
`level`, `service`, `message`, `status` and `timestamp`. The log schema's “warning”
and “ISO 8061” wording differs from the environment table; inspect emitted
records rather than building a parser from that prose alone.

Audit logs and Analytics are distinct from console logs. Analytics requires
paid access and audit logging; daily/weekly/monthly views separate active users,
web search/Ask/navigation, MCP and direct-API usage. Passive web repository
listings are excluded. Retention affects available history; see
[administration](administration-and-licensing.md).

There are three separate outbound-data decisions:

1. **Model/connector traffic:** configured providers and connectors receive task
   context. `SOURCEBOT_LLM_USER_EMAIL_HEADER_ENABLED=false` by default; enabling
   it adds the authenticated user's lower-cased email in
   `X-Sourcebot-User-Email`. Anonymous calls omit it.
2. **Product telemetry:** PostHog usage/performance metadata is enabled by default.
   `SOURCEBOT_TELEMETRY_DISABLED=true` opts out; verify the startup log says
   `Disabling telemetry since SOURCEBOT_TELEMETRY_DISABLED was set.`
3. **Service ping:** separately, HTTPS to `deployments.sourcebot.dev:443` every
   24 hours by default. Payload includes installation ID, hostname/version,
   user/repo/activity counts, deployment type, telemetry/model flags, activation
   code when present and best-effort CPU/memory/disk metadata. The docs exclude
   code, prompts, credentials and individual user information, not all metadata.
   Online licensing depends on this ping; telemetry opt-out is not its switch.

Do not promise zero egress merely because Sourcebot is self-hosted. Verify the
actual selected controls and authorized network destinations.

## Official sources

- [Config and overrides](https://docs.sourcebot.dev/docs/configuration/config-file.md), [environment variables](https://docs.sourcebot.dev/docs/configuration/environment-variables.md)
- [Indexing schema](https://docs.sourcebot.dev/docs/connections/indexing-your-code.md), [Redis TLS](https://docs.sourcebot.dev/docs/deployment/infrastructure/redis.md)
- [Structured logging](https://docs.sourcebot.dev/docs/configuration/structured-logging.md), [Analytics](https://docs.sourcebot.dev/docs/features/analytics.md)
- [Telemetry](https://docs.sourcebot.dev/docs/misc/telemetry.md), [service ping](https://docs.sourcebot.dev/docs/misc/service-ping.md)
