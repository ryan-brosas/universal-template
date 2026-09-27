# Deployment, capacity and upgrades

Use this for a requested installation or migration, not as a prerequisite for
research. Establish the installed version, data volumes, secret ownership and
rollback plan first. A major-version upgrade can change authorization and
entitlements as well as infrastructure.

## Architecture and sizing

Sourcebot combines a Next.js web server, asynchronous Node backend worker,
Zoekt trigram search, PostgreSQL transactional data, Redis/BullMQ queues and a
persistent `.sourcebot/` cache. In v5, Postgres and Redis are external to the
application image; Compose and Helm can still provide them as separate services.
Older architecture prose about embedded services does not override this change.
The documented scaling model is vertical, not horizontal.

The sizing guide gives these starting estimates, not capacity guarantees:

| Repositories | CPU cores | RAM | Disk |
| --- | --- | --- | --- |
| Up to 100 | 2 | 4 GB | 50 GB |
| 100–500 | 4 | 8 GB | 100 GB |
| 500–2,000 | 8 | 32 GB | 250 GB |
| 2,000+ | 16+ | 64+ GB | 500+ GB |

Budget roughly 2–3 times source size for clones/indexes; indexing many branches
can multiply storage further. Monitor disk exhaustion, indexing failures,
search-time CPU, memory limits and latency. More RAM improves the page cache;
try it before CPU for persistently slow search. Reducing connection/index job
concurrency lowers indexing peaks but extends completion time. Managed Postgres
and Redis are recommended for stability. Audit storage is a separate budget;
see [administration](administration-and-licensing.md).

## Docker Compose

The official guide requires current Docker/Compose and at least 4 GB RAM.
Node.js 18+ is needed for `npx setup-sourcebot`, not as a separate host prerequisite
for a manually deployed container. The CLI generates a new directory, config and
Compose file. Alternatively, obtain the release-appropriate official Compose
file, create `config.json`, supply secrets and start the stack. Do not overwrite
an existing deployment with the quick-start example.

In v5, provide `AUTH_SECRET`, `SOURCEBOT_ENCRYPTION_KEY`, `DATABASE_URL` and
`REDIS_URL`. Mount config/data and set `CONFIG_PATH`; use the public `AUTH_URL`
when serving a domain. For a **new** deployment the docs suggest
`openssl rand -base64 33` and `openssl rand -base64 24` for the respective secrets.
For an upgrade, preserve existing values instead. Never print them into a report.

## Kubernetes / Helm

The indexed Kubernetes guide redirects to the official
[chart README](https://github.com/sourcebot-dev/sourcebot-helm-chart).
The chart repository is `https://sourcebot-dev.github.io/sourcebot-helm-chart`;
the chart is `sourcebot/sourcebot`. Read the matching README and `values.yaml`
before a requested install/upgrade rather than assuming current `main` matches
an older release.

- Supply config using `sourcebot.config` in values, or the chart's documented
  `--set-json` mechanism, and pass the reviewed values file.
- Prefer existing Kubernetes Secrets for auth/encryption, database/cache
  passwords and licenses. `sourcebot.additionalEnvSecrets`, `additionalEnv` and
  `envFrom` cover secret-key, plain-value and whole-Secret/ConfigMap injection.
- Postgres and Redis/Valkey subcharts deploy by default. For externally managed
  services use `postgresql.deploy: false` / `redis.deploy: false` and the matching
  connection values. The key is `redis` even where the component is named Valkey.
- Ingress is opt-in. Default volumes are 10 GiB for Sourcebot and 8 GiB each for
  Postgres and Valkey; resize from actual workload needs.
- Default `RollingUpdate` can stall with a multi-node `ReadWriteOnce` volume.
  Choose compatible `ReadWriteMany` storage, same-node affinity, or `Recreate`
  with acknowledged downtime. Do not prescribe one without inspecting storage.
- Uninstall preserves PVCs by default. Deleting PVCs destroys data; it is a
  separate destructive operation requiring confirmation, not routine cleanup.

## Version-specific migration checklist

Back up and test restoration before migration. Explain any cache removal,
credential rotation, database move or service interruption and obtain approval.
Read the full applicable guide before executing its commands.

| Boundary | Required decisions before replacement |
| --- | --- |
| v2 → v3 | Convert unnamed `repos` config to named single-host `connections`; the historical guide requires a cache wipe/full reindex and removes the then-supported local-file/raw-remote-`.git` routes. Do not project that historical removal onto today's documented local Git support. |
| v3 → v4 | Authentication becomes required by default and multi-tenancy is removed. Set `AUTH_URL`, register the first Owner and review access approval. Existing auth deployments remove `SOURCEBOT_AUTH_ENABLED`; former multi-tenant deployments remove `SOURCEBOT_TENANCY_MODE` and follow the cache migration. |
| v4 → v5 | Ask, MCP and role management become paid. New free-plan users become Owners; existing Members keep their roles. Evaluate that access change before inviting more users or upgrading. |
| v4 → v5 infrastructure | Embedded Postgres/Redis are removed. Dump embedded Postgres while v4 still runs, copy the dump out and restore to external Postgres; v5 no longer contains `pg_dump`. Redis queue data is transient. Configure both service URLs before starting v5. |
| v4 → v5 secrets | Recover auto-generated values from `.authjs-secret` and `.secret` under the old `DATA_CACHE_DIR` securely, then provide them explicitly. Missing values prevent startup; a changed encryption key makes stored protected data unreadable; a changed auth secret signs users out. |
| v5.0.2 SSO | Legacy `AUTH_EE_*` variables for GitHub, GitLab, Google, Okta, Keycloak and Entra providers are no longer read. Migrate those providers to `identityProviders` with `purpose: "sso"`; do not remove unrelated supported GCP-IAP controls by prefix matching. |

After migration, check service startup, login/provider buttons, owner/member
behavior, repository visibility, a known search and file read, and licensed
features. A healthy container alone is insufficient. Staying on a pinned earlier
release is an explicit compatibility choice, not permission to bypass licensing.

## Official sources

- [Deployment](https://docs.sourcebot.dev/docs/deployment/deploy-sourcebot.md), [Compose](https://docs.sourcebot.dev/docs/deployment/docker-compose.md), [Helm redirect](https://docs.sourcebot.dev/docs/deployment/k8s.md)
- [Architecture](https://docs.sourcebot.dev/docs/deployment/infrastructure/architecture.md), [sizing](https://docs.sourcebot.dev/docs/deployment/sizing-guide.md), [scalability](https://docs.sourcebot.dev/docs/misc/scalability.md)
- [v2 → v3](https://docs.sourcebot.dev/docs/upgrade/v2-to-v3-guide.md), [v3 → v4](https://docs.sourcebot.dev/docs/upgrade/v3-to-v4-guide.md), [v4 → v5](https://docs.sourcebot.dev/docs/upgrade/v4-to-v5-guide.md)
