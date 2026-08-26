<!-- capsule-v2 -->
# Image naming & push — how are build/production image names derived per pack, preview, and registry config?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** Which image reference is built, which is pushed, which runs — and when does a push failure fail the deployment?

## generate_image_names / previewImageTag / push_to_docker_registry
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:generate_image_names` (lines 1175–1218), `previewImageTag` (1219–1239), `push_to_docker_registry` (1093–1141), `validateDockerRegistryImageConfiguration` (1160–1174).
**Signature:** `private function generate_image_names(): void`, `private function previewImageTag(bool $build = false): string`, `private function push_to_docker_registry()`.
**Data Shape:** `$this->build_image_name` / `$this->production_image_name`; tag budget 128 chars; dockerImageTag = substr(commit, 0, 128); preview prefix `pr-<id>-` with optional `-build` suffix.

### Decisive source
```php
} else {
    $this->dockerImageTag = str($this->commit)->substr(0, 128);
    if ($this->application->docker_registry_image_name) {
        $this->build_image_name   = "{$this->application->docker_registry_image_name}:{$this->dockerImageTag}-build";
        $this->production_image_name = "{$this->application->docker_registry_image_name}:{$this->dockerImageTag}";
    } else {
        $this->build_image_name   = "{$this->application->uuid}:{$this->dockerImageTag}-build";
        $this->production_image_name = "{$this->application->uuid}:{$this->dockerImageTag}";
    }
}
```
push guard matrix:
```php
if ($this->restart_only) return;
if ($this->application->build_pack === 'dockerimage') return;
...
if ($this->server->isSwarm() && $this->build_pack !== 'dockerimage') { $forceFail = true; }
if ($this->application->additional_servers->count() > 0) { $forceFail = true; }
```

**Flow:** names derived per branch: inline-dockerfile apps use `<registry|uuid>:latest` + `:build`; dockerimage packs use the user image verbatim (sha256- digests supported via `@sha256:<hash>`); previews get `pr-<id>-<sanitized commit|deployment_uuid>` tags where non-regex chars become `-` and HEAD falls back to the deployment uuid; normal builds use first-128-of-commit. push: skip for restart-only/dockerimage/additional-server replicas; registry presence checked by listing local images then `docker push` inside the builder; extra custom tag pushed best-effort (`ignore_errors`) only for pr-0; failures throw DeploymentException whenever forceFail conditions hold.
**Invariant:** build vs production image are DIFFERENT tags of the same name so a failed build never overwrites the running tag; image/tag strings are validated against ValidationPatterns at construction (invalid chars throw before any work); the sha128 truncation plus pr-prefix sanitization keep refs within Docker's tag grammar. Registry-push failure fails the deployment EXCEPT code 69420 path in failed() leaves the currently running version untouched.
**Probe:** `tests/Unit/ApplicationDeploymentRailpackBuildxMetadataTest.php` and `tests/Unit/GitLsRemoteParsingTest.php` pin adjacent naming/commit plumbing; live probe: `grep -n "substr(0, 128)" app/Jobs/ApplicationDeploymentJob.php` → exactly one line (1205).
**Retrieve:** search_graph project ext-coolify query "ApplicationDeploymentJob generate_image_names" → Method node app/Jobs/ApplicationDeploymentJob.php.

## Verdict
Adopt dual-tag naming, commit-derived tag budgets, and the push force-fail matrix as portable registry behavior; adapt uuid source to your resource ids; omit railpack/buildx metadata specifics.
