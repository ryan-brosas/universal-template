<!-- capsule-v2 -->
# Build-pack router — what is the dispatch order from job start through builder prep to the right build pack?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** Given an application, in what order does the deployment job decide between restart-only, dockerimage, PR preview, dockerfile/compose/static/nixpacks/railpack — and what does it probe before building?

## decide_what_to_do + handle() preamble + detectBuildKitCapabilities
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:decide_what_to_do` (lines 501–528), `handle` (299–424), `detectBuildKitCapabilities` (426–500).
**Signature:** `private function decide_what_to_do(): void`, `private function detectBuildKitCapabilities(): void`.
**Data Shape:** `$application->build_pack ∈ {dockerimage, dockerfile, dockercompose, static, nixpacks, railpack}`; capability flags `dockerBuildkitSupported`, `dockerBuildxAvailable`, `dockerSecretsSupported` set on the job.

### Decisive source
```php
if ($this->restart_only) {
    $this->just_restart(); return;
} elseif ($this->application->build_pack === 'dockerimage') {
    $this->deploy_dockerimage_buildpack();
} elseif ($this->pull_request_id !== 0) {
    $this->deploy_pull_request();
} elseif ($this->application->dockerfile) {
    $this->deploy_simple_dockerfile();
} elseif ($this->application->build_pack === 'dockercompose') {
    ...
} else {
    throw new DeploymentException("Unsupported build pack: {$this->application->build_pack}");
}
$this->post_deployment();
```

**Flow:** __construct rehydrates queue row → application → server/destination and clamps flags (`restart_only` is forced false for dockerimage/dockerfile packs; `force_rebuild` forced true when build cache disabled) → handle() checks pre-cancel, stores private key, builds `--add-host name:ip` map from `docker network inspect` (skipping coolify-proxy and `-<12digits>` replicas), picks a random build server when enabled (falls back to deploy server with a log line), probes Docker version ≥ 18.09 → buildx presence → fallback `DOCKER_BUILDKIT=1 docker build --help | grep --progress` test → optional `--secret` support, then routes.
**Invariant:** The router order IS behavior: an app with inline `dockerfile` content never reaches `deploy_dockerfile_buildpack`, and PR previews route before pack checks except dockerimage/dockercompose which are checked inside `deploy_pull_request` again. Capability detection failures degrade to all-false flags with a log entry instead of failing the deployment. `post_deployment()` runs after EVERY branch including exceptions thrown by packs? No — only after successful return; failure goes through `failed()`.
**Probe:** `grep -c "Unsupported build pack" app/Jobs/ApplicationDeploymentJob.php` matches exactly 1 line (~line 523, verified live); `tests/Unit/ApplicationDeploymentTypeTest.php` pins pack classification.
**Retrieve:** search_graph project ext-coolify query "ApplicationDeploymentJob decide_what_to_do" → Method node app/Jobs/ApplicationDeploymentJob.php.

## Verdict
Adopt ordered dispatch + pre-build capability probing + add-host network discovery as portable orchestrator design; adapt the probe commands to your container runtime; omit Coolify helper-image specifics (`coolifyHelperImage()` versioning).
