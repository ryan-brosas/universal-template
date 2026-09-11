<!-- capsule-v2 -->
# Env var pipeline — which env vars exist at build time vs runtime, and in what order must .env be written?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** A porter writing the .env at the wrong moment or including volatile vars in builds breaks Docker layer caching and secret hygiene — where exactly are the boundaries?

## generate_coolify_env_variables / generate_runtime_environment_variables / save_runtime_environment_variables
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:generate_coolify_env_variables` (lines 3072–3168), `generate_runtime_environment_variables` (1326–1494), `save_runtime_environment_variables` (1504–1611), `save_buildtime_environment_variables` (1842–1879).
**Signature:** `protected function generate_coolify_env_variables(bool $forBuildTime = false): Collection`; `private function generate_runtime_environment_variables(): Collection`.
**Data Shape:** Env collections of `KEY=value` strings; Coolify injected keys: SOURCE_COMMIT, COOLIFY_URL/FQDN (swapped by `compose_parsing_version >= 3`), COOLIFY_BRANCH, COOLIFY_RESOURCE_UUID, COOLIFY_CONTAINER_NAME, plus SERVICE_FQDN_/SERVICE_URL_/SERVICE_NAME_ for compose services.

### Decisive source
```php
// Only add SOURCE_COMMIT for runtime OR when explicitly enabled for build-time
// SOURCE_COMMIT changes with each commit and breaks Docker cache if included in build
if (! $forBuildTime || $this->application->settings->include_source_commit_in_build) {
    ...
}
// Only add COOLIFY_CONTAINER_NAME for runtime (not build-time) - it changes every deployment and breaks Docker cache
if (! $forBuildTime) { ... COOLIFY_CONTAINER_NAME ... }
```
and in deploy_pull_request():
```php
// Save build-time .env file BEFORE the build
$this->save_buildtime_environment_variables();
$this->generate_build_env_variables();
...
$this->build_image();
// This overwrites the build-time .env with ALL variables (build-time + runtime)
$this->save_runtime_environment_variables();
```

**Flow:** build-time env = filtered coolify envs + build args/secrets → .env written before build → image built (build secrets mounted as `--secret`/ENV when BuildKit supports it, else ARG injection into Dockerfile via `modify_dockerfile_for_secrets`) → after build the SAME path `.env` is overwritten with runtime superset → compose `up` reads it. Runtime generation orders: coolify envs first; SERVICE_* generated from domains/compose for dockercompose; user runtime vars sorted so vars whose VALUE references `$SERVICE_` come last (dependency order); PORT defaults to first exposed port, HOST to 0.0.0.0 when unset. Preview branch: preview vars win; production values fill ONLY missing keys, and only when any preview var exists — prevents leaking prod secrets into unconfigured previews.
**Invariant:** Volatile-per-deployment values must never enter the build-time env or Docker cache invalidates every build; runtime .env write happens strictly after `build_image()` because it overwrites the build-time file; SERVICE_ key names are underscore-normalized (`normalizeComposeServiceName`) while values keep original service names.
**Probe:** `tests/Unit/ApplicationDeploymentEmptyEnvTest.php` pins that dockerimage/dockercompose packs require an empty `.env` (compose `env_file` contract); `tests/Unit/ApplicationDeploymentNixpacksNullEnvTest.php` and `tests/Unit/BashEnvEscapingTest.php` pin escaping/null handling.
**Retrieve:** search_graph project ext-coolify query "generate_env_variables coolify_envs" → Method nodes around app/Jobs/ApplicationDeploymentJob.php 3072+.

## Verdict
Adopt the two-phase .env protocol and volatile-var exclusion as pure behavior; adapt key names (SERVICE_*, COOLIFY_*) to your platform's conventions; omit nixpacks/railpack plan-file specifics unless porting those builders.
