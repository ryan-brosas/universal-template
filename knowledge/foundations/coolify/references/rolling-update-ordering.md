<!-- capsule-v2 -->
# Rolling update ordering — why does start-before-stop plus health-gate make zero-downtime deploys safe?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** In what order are new container started, health-checked, and old containers removed — and when is the safe order impossible?

## rolling_update → health_check → stop_running_container
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:rolling_update` (lines 1934–1983), `health_check` (1985–2063), `stop_running_container` (4021–4064).
**Signature:** `private function rolling_update(): void`, `private function health_check(): void`, `private function stop_running_container(bool $force = false)`.
**Data Shape:** `$this->newVersionIsHealthy: bool`; healthcheck knobs from application: `health_check_start_period`, `health_check_retries`, `health_check_interval`, `health_check_type (cmd|path)`.

### Decisive source
```php
$this->application_deployment_queue->addLogEntry('Rolling update started.');
$this->start_by_compose_file();
$this->health_check();
$this->stop_running_container();
```
and the guard inside stop_running_container:
```php
if ($this->newVersionIsHealthy || $force) {
    ... graceful_shutdown_container(...) ...
} else {
    ...
    $this->application_deployment_queue->addLogEntry('New container is not healthy, rolling back to the old container.');
    $this->failDeployment();
    $this->graceful_shutdown_container($this->container_name);   // remove NEW, keep OLD
}
```

**Flow:** Swarm → `docker stack deploy`. Non-swarm with blocking conditions (host port mappings, consistent container name, custom internal name, PR preview, custom `--ip/--ip6` in run options) → log each reason, force-stop old first (`stop_running_container(force: true)`), then start — brief downtime accepted because name/port collisions make overlap impossible. Otherwise: start new compose project alongside old → poll `docker inspect --format='{{json .State.Health.Status}}'` after start period, up to retries × interval seconds, logging last health log line + exit code per attempt → healthy ⇒ mark app running and remove old containers; unhealthy or stuck-in-starting ⇒ dump last 100 log lines via `query_logs()`, fail deployment, remove only the NEW container.
**Invariant:** Old containers may be removed ONLY after `newVersionIsHealthy` (or explicit force); the removal filter excludes the current container name for pr-0 so replicas of previous generations go but the just-started one stays; healthcheck disabled + no Dockerfile HEALTHCHECK short-circuits to healthy=true (deploy proceeds unverified). PR previews always take the stop-first path.
**Probe:** `grep -n "Rolling update started" app/Jobs/ApplicationDeploymentJob.php` matches exactly 2 lines (1939 swarm branch and 1973 non-swarm branch — verified live); `tests/Unit/ContainerHealthStatusTest.php` pins health-status parsing helpers.
**Retrieve:** search_graph project ext-coolify query "graceful_shutdown_container removeContainerWithTimeout rolling_update" resolves all three methods with exact line spans.

## Verdict
Adopt start→verify→cutover ordering and its documented exceptions as portable deploy semantics; adapt docker inspect polling to your orchestrator's health API; omit swarm stack-deploy specifics.
