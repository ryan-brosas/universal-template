<!-- capsule-v2 -->
# Deployment queue admission — how does Coolify admit, skip, and drain deployments without double-running one?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** When a deploy request arrives, when is a row created vs an existing deployment returned, and who starts QUEUED rows later?

## queue_application_deployment → next_queuable → queue_next_deployment
**Path/Symbol:** `bootstrap/helpers/applications.php:queue_application_deployment` (lines 14–108), `bootstrap/helpers/applications.php:next_queuable` (lines 141–166), `bootstrap/helpers/applications.php:queue_next_deployment` (lines 119–139).
**Signature:** `queue_application_deployment(Application $application, string $deployment_uuid, ?int $pull_request_id = 0, ?string $commit = null, bool $force_rebuild = false, bool $is_webhook = false, bool $is_api = false, bool $restart_only = false, ?string $git_type = null, bool $no_questions_asked = false, ?Server $server = null, ?StandaloneDocker $destination = null, bool $only_this_server = false, bool $rollback = false, ?string $docker_registry_image_tag = null): array`; `next_queuable(string $server_id, string $application_id, string $commit = 'HEAD', int $pull_request_id = 0): bool`.
**Data Shape:** Input: Application + request flags. Reads/writes `ApplicationDeploymentQueue` rows with status enum values `queued|in_progress|finished|failed|cancelled-by-user`. Returns `['status' => 'queue_full'|'skipped'|'queued', ...]`.

### Decisive source
```php
$existing_deployment = ApplicationDeploymentQueue::where('application_id', $application_id)
    ->where('commit', $commit)
    ->where('pull_request_id', $pull_request_id)
    ->where('docker_registry_image_tag', $docker_registry_image_tag)
    ->whereIn('status', [ApplicationDeploymentStatus::IN_PROGRESS->value, ApplicationDeploymentStatus::QUEUED->value])
    ->first();

if ($existing_deployment) {
    if (! $force_rebuild && ! $rollback && ! $no_questions_asked) {
        return [
            'status' => 'skipped',
            'message' => 'Deployment already queued for this commit.',
            ...
```

**Flow:** (1) compute server/destination ids; (2) count QUEUED rows for the server against `deployment_queue_limit ?? 25` → `queue_full` short-circuit; (3) dedupe lookup on (application_id, commit, pull_request_id, docker_registry_image_tag) among IN_PROGRESS+QUEUED → `skipped` unless force/rollback/no_questions_asked; (4) create the queue row; (5) `$no_questions_asked` flips straight to IN_PROGRESS and dispatches; else `next_queuable()` decides IN_PROGRESS-now vs stays-QUEUED; (6) every terminal transition elsewhere calls `queue_next_deployment($application)` which walks that server's QUEUED rows oldest-first and dispatches each that passes `next_queuable()`.
**Invariant:** `next_queuable` gates on TWO axes — no other IN_PROGRESS row for the same (application, pull_request_id), AND active deployments on the server < `concurrent_builds`. Normal deploys and PR deploys of the same app may run concurrently because PR id differs; the per-server build limit is global across applications. The drain loop intentionally iterates ALL queued rows (not just the first): a blocked head must not block non-conflicting successors.
**Probe:** `tests/Feature/ApplicationPreviewQueueAdvancementTest.php` — after preview cleanup cancels the active PR-42 deployment, the queued pr-0 deployment's status becomes `in_progress` and exactly one `ApplicationDeploymentJob` is pushed with its id.
**Retrieve:** search_graph project ext-coolify query "queue_next_deployment next_queuable queue_application_deployment" resolves all three functions in bootstrap/helpers/applications.php.

## Verdict
Adopt dedupe key + two-axis admission + drain-on-transition as portable orchestrator behavior; adapt Eloquent/Cache specifics; omit the Laravel helper-global placement (port as a service). Coverage caveat: bootstrap/helpers are indexed in full mode but coverage tooling reports best-effort only.
